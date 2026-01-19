import fastf1, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ========= CONFIG =========
YEAR = 2025
GP = "Spain Grand Prix"
SESSION = "R"
TOP_N = 10
CACHE_DIR = Path("/content/fastf1_cache")

# ========= CACHE =========
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ========= LOAD SESSION =========
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

laps = session.laps.copy()
laps = laps[laps["IsAccurate"]]
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# ========= TOP 10 FINISHERS =========
drivers = (
    session.results
    .sort_values("Position")
    .head(TOP_N)["Abbreviation"]
    .tolist()
)

laps = laps[
    laps["Driver"].isin(drivers) &
    laps["PitInTime"].isna() &
    laps["PitOutTime"].isna()
]

# ========= ANALYSIS PER STINT =========
summary = []

plt.figure(figsize=(15,7))

for (d, stint), dl in laps.groupby(["Driver", "Stint"]):

    if len(dl) < 5:
        continue

    compound = dl["Compound"].iloc[0]

    # ---- remove outliers (IQR) ----
    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1
    dl = dl[
        (dl["LapTimeSec"] >= q1 - 1.5 * iqr) &
        (dl["LapTimeSec"] <= q3 + 1.5 * iqr)
    ]

    if len(dl) < 5:
        continue

    # ---- pace & degradation ----
    avg_pace = dl["LapTimeSec"].mean()
    slope = np.polyfit(dl["TyreLife"], dl["LapTimeSec"], 1)[0]

    summary.append({
        "Driver": d,
        "Stint": stint,
        "Compound": compound,
        "Laps": len(dl),
        "AvgPace_s": avg_pace,
        "TyreDeg_s_per_lap": slope
    })

    # ---- plot pace trend ----
    plt.plot(
        dl["LapNumber"],
        dl["LapTimeSec"],
        label=f"{d} | Stint {stint} | {compound}"
    )

plt.title("Top 10 – Stint-based Race Pace\n(Spain GP 2025)")
plt.xlabel("Lap Number")
plt.ylabel("Lap Time (s)")
plt.grid(alpha=0.3)
plt.legend(ncol=3, fontsize=9)
plt.tight_layout()
plt.show()

# ========= SUMMARY TABLE =========
summary_df = pd.DataFrame(summary)
summary_df.sort_values(["Driver","Stint"])
