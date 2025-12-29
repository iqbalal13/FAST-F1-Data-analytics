import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# =============================
# CONFIG
# =============================
YEAR = 2025
GP = "Bahrain Grand Prix"
SESSION = "R"
CACHE_DIR = "cache"

# =============================
# SETUP
# =============================
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl()
plt.style.use("dark_background")

# =============================
# LOAD SESSION
# =============================
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

# =============================
# LOAD LAPS
# =============================
laps = session.laps
laps = laps[laps["IsAccurate"] == True].copy()
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# =============================
# TOP 10 FINISHERS
# =============================
results = session.results.sort_values("Position").head(10)
drivers = results["Abbreviation"].tolist()
laps = laps[laps["Driver"].isin(drivers)]

# =============================
# REMOVE PIT LAPS
# =============================
laps = laps[
    laps["PitInTime"].isna() &
    laps["PitOutTime"].isna()
]

# =============================
# REMOVE OUTLIERS (PER DRIVER)
# =============================
clean_laps = []

for drv in drivers:
    drv_laps = laps[laps["Driver"] == drv]

    q1 = drv_laps["LapTimeSec"].quantile(0.25)
    q3 = drv_laps["LapTimeSec"].quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    drv_clean = drv_laps[
        (drv_laps["LapTimeSec"] >= lower) &
        (drv_laps["LapTimeSec"] <= upper)
    ]

    clean_laps.append(drv_clean)

clean_laps = pd.concat(clean_laps)

# =============================
# COLORS (STABLE)
# =============================
cmap = plt.cm.get_cmap("tab10", len(drivers))
driver_colors = {drv: cmap(i) for i, drv in enumerate(drivers)}

# =============================
# PLOT CLEAN RACE PACE
# =============================
plt.figure(figsize=(15,7))

for drv in drivers:
    drv_laps = clean_laps[clean_laps["Driver"] == drv]

    plt.plot(
        drv_laps["LapNumber"],
        drv_laps["LapTimeSec"],
        color=driver_colors[drv],
        linewidth=1.8,
        label=drv
    )

plt.title(
    "Clean Race Pace – Top 10\nBahrain GP 2025",
    fontsize=15
)
plt.xlabel("Lap Number")
plt.ylabel("Lap Time (seconds)")
plt.grid(alpha=0.25)
plt.legend(title="Drivers", ncol=5, fontsize=9)
plt.tight_layout()
plt.show()
