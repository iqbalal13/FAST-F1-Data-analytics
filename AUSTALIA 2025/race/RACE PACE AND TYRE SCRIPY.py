import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# =============================
# CONFIG
# =============================
YEAR = 2025
GP = "Australian Grand Prix"
SESSION = "R"
CACHE_DIR = "cache"

# =============================
# SETUP
# =============================
fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl()
plt.style.use("dark_background")

# =============================
# LOAD SESSION
# =============================
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

# =============================
# LOAD & CLEAN LAPS
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
# COLOR SETUP (VERSION-PROOF)
# =============================
cmap = plt.cm.get_cmap("tab10", len(drivers))
driver_colors = {drv: cmap(i) for i, drv in enumerate(drivers)}

tyre_colors = {
    "SOFT": "red",
    "MEDIUM": "gold",
    "HARD": "white",
    "INTERMEDIATE": "green",
    "WET": "blue"
}

# =============================
# PLOT
# =============================
plt.figure(figsize=(14,7))

for drv in drivers:
    drv_laps = laps[laps["Driver"] == drv]

    # Race pace line
    plt.plot(
        drv_laps["LapNumber"],
        drv_laps["LapTimeSec"],
        linewidth=1.8,
        color=driver_colors[drv],
        label=drv
    )

    # Tyre compound markers
    for compound, group in drv_laps.groupby("Compound"):
        plt.scatter(
            group["LapNumber"],
            group["LapTimeSec"],
            s=36,
            color=tyre_colors.get(compound, "gray"),
            edgecolors="black",
            zorder=3
        )

# =============================
# LABELS & STYLE
# =============================
plt.title(
    "Race Pace & Tyre Strategy – Top 10\nAustralian GP 2025",
    fontsize=15
)
plt.xlabel("Lap Number")
plt.ylabel("Lap Time (seconds)")

plt.grid(alpha=0.25)
plt.legend(title="Drivers", ncol=5, fontsize=9)
plt.tight_layout()
plt.show()


