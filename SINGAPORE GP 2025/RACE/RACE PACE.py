import fastf1, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ===== CONFIG =====
YEAR = 2025
GP = "Singapore Grand Prix"
SESSION = "R"
COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]
TOP_N = 10
CACHE_DIR = Path("/content/fastf1_cache")

# ===== CACHE =====
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ===== LOAD =====
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

laps = session.laps
laps = laps[laps["IsAccurate"]].copy()
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

drivers = (
    session.results
    .sort_values("Position")
    .head(TOP_N)["Abbreviation"]
    .tolist()
)

laps = laps[
    laps["Driver"].isin(drivers) &
    laps["PitInTime"].isna() &
    laps["PitOutTime"].isna() &
    laps["Compound"].isin(COMPOUNDS)
]

# ===== REMOVE OUTLIERS (IQR per driver, compound, stint) =====
clean = []

for (d, c, s), dl in laps.groupby(["Driver","Compound","Stint"]):
    if len(dl) < 5:
        continue
    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1
    dl = dl[(dl["LapTimeSec"] >= q1-1.5*iqr) & (dl["LapTimeSec"] <= q3+1.5*iqr)]
    clean.append(dl)

clean = pd.concat(clean)

# ===== CALCULATE DEGRADATION SLOPE =====
records = []

for (d, c), dl in clean.groupby(["Driver","Compound"]):
    stint_id = dl.groupby("Stint").size().idxmax()
    st = dl[dl["Stint"] == stint_id]
    if len(st) < 5:
        continue
    slope = np.polyfit(st["TyreLife"], st["LapTimeSec"], 1)[0]
    records.append({"Driver": d, "Compound": c, "Degradation_s_per_lap": slope})

deg = pd.DataFrame(records)

# ===== PLOT =====
pivot = deg.pivot(index="Driver", columns="Compound", values="Degradation_s_per_lap")
pivot.plot(kind="bar", figsize=(14,6))

plt.title("Tyre Degradation Comparison – SOFT vs MEDIUM VS HARD\nTop 10 Finishers")
plt.ylabel("Degradation Rate (s/lap)")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.show()

pivot
