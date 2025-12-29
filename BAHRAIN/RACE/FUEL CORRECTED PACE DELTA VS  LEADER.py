import fastf1, os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# ===== CONFIG =====
YEAR, GP, SESSION = 2025, "Bahrain Grand Prix", "R"
CACHE_DIR = "cache"

FUEL_START = 110        # kg
FUEL_BURN = 1.5         # kg/lap
FUEL_PENALTY = 0.033    # sec/kg
ROLL = 3

os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ===== LOAD SESSION =====
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

laps = session.laps
laps = laps[laps["IsAccurate"]].copy()
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# ===== TOP 10 =====
drivers = (
    session.results.sort_values("Position")
    .head(10)["Abbreviation"]
    .tolist()
)
leader = drivers[0]

laps = laps[laps["Driver"].isin(drivers)]
laps = laps[laps["PitInTime"].isna() & laps["PitOutTime"].isna()]

# ===== OUTLIER REMOVAL =====
clean = []
for d in drivers:
    dl = laps[laps["Driver"] == d]
    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1
    clean.append(dl[(dl["LapTimeSec"] >= q1-1.5*iqr) & (dl["LapTimeSec"] <= q3+1.5*iqr)])

clean = pd.concat(clean)

# ===== FUEL CORRECTION =====
clean["FuelRemaining"] = FUEL_START - (clean["LapNumber"] - 1) * FUEL_BURN
clean["FuelCorrected"] = clean["LapTimeSec"] - clean["FuelRemaining"] * FUEL_PENALTY

clean["Rolling"] = (
    clean.groupby("Driver")["FuelCorrected"]
    .rolling(ROLL, center=True).mean()
    .reset_index(level=0, drop=True)
)

leader_pace = (
    clean[clean["Driver"] == leader][["LapNumber","Rolling"]]
    .rename(columns={"Rolling":"LeaderRolling"})
)

clean = clean.merge(leader_pace, on="LapNumber", how="left")
clean["DeltaVsLeader"] = clean["Rolling"] - clean["LeaderRolling"]

# ===== PLOT =====
plt.figure(figsize=(15,6))
colors = plt.cm.tab10(np.linspace(0,1,len(drivers)))

for d,c in zip(drivers, colors):
    dlap = clean[clean["Driver"] == d]
    plt.plot(dlap["LapNumber"], dlap["DeltaVsLeader"], color=c, label=d)

plt.axhline(0, linestyle="--", color="white")
plt.title("Fuel-Corrected Delta Pace vs Leader\nBahrain GP 2025")
plt.xlabel("Lap")
plt.ylabel("Delta to Leader (s)")
plt.grid(alpha=0.3)
plt.legend(ncol=5)
plt.tight_layout()
plt.show()
