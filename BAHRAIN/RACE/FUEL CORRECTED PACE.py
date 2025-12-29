import fastf1, os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# =============================
# CONFIG
# =============================
YEAR = 2025
GP = "Bahrain Grand Prix"
SESSION = "R"
CACHE_DIR = "cache"

FUEL_START_KG = 110        # typical F1 race fuel
FUEL_BURN_PER_LAP = 1.5   # kg per lap
FUEL_PENALTY = 0.033      # sec per kg (0.03–0.035 standard)

ROLL = 3

# =============================
# SETUP
# =============================
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# =============================
# LOAD SESSION
# =============================
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

# =============================
# LOAD & CLEAN LAPS
# =============================
laps = session.laps
laps = laps[laps["IsAccurate"]].copy()
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# =============================
# TOP 10 FINISHERS
# =============================
drivers = (
    session.results
    .sort_values("Position")
    .head(10)["Abbreviation"]
    .tolist()
)

laps = laps[laps["Driver"].isin(drivers)]

# =============================
# REMOVE PIT LAPS
# =============================
laps = laps[
    laps["PitInTime"].isna() &
    laps["PitOutTime"].isna()
]

# =============================
# REMOVE OUTLIERS (IQR)
# =============================
clean = []
for d in drivers:
    dl = laps[laps["Driver"] == d]
    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1
    clean.append(
        dl[
            (dl["LapTimeSec"] >= q1 - 1.5 * iqr) &
            (dl["LapTimeSec"] <= q3 + 1.5 * iqr)
        ]
    )

clean = pd.concat(clean)

# =============================
# FUEL MODEL
# =============================
clean["FuelRemaining"] = (
    FUEL_START_KG -
    (clean["LapNumber"] - 1) * FUEL_BURN_PER_LAP
)

clean["FuelCorrection"] = clean["FuelRemaining"] * FUEL_PENALTY

clean["FuelCorrectedPace"] = (
    clean["LapTimeSec"] - clean["FuelCorrection"]
)

# =============================
# ROLLING AVERAGE
# =============================
clean["FuelCorrectedRolling"] = (
    clean.groupby("Driver")["FuelCorrectedPace"]
    .rolling(ROLL, center=True)
    .mean()
    .reset_index(level=0, drop=True)
)

# =============================
# COLORS
# =============================
colors = plt.cm.tab10(np.linspace(0, 1, len(drivers)))

# =============================
# PLOT
# =============================
plt.figure(figsize=(15,6))

for d,c in zip(drivers, colors):
    dl = clean[clean["Driver"] == d]
    plt.plot(
        dl["LapNumber"],
        dl["FuelCorrectedRolling"],
        color=c,
        linewidth=2,
        label=d
    )

plt.title(
    "Fuel-Corrected Clean Race Pace (Rolling Avg)\nBahrain GP 2025",
    fontsize=15
)
plt.xlabel("Lap Number")
plt.ylabel("Fuel-Corrected Lap Time (s)")
plt.grid(alpha=0.3)
plt.legend(ncol=5)
plt.tight_layout()
plt.show()
