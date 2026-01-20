import fastf1, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ========= CONFIG =========
YEAR = 2025
GP = "Belgian Grand Prix"
SESSION = "R"
COMPOUND = "INTERMEDIATE"      # SOFT / MEDIUM / HARD
TOP_N = 10             # Top N finishers
CACHE_DIR = Path("/content/fastf1_cache")

# ========= CACHE =========
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ========= LOAD SESSION =========
session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

laps = session.laps.copy()
laps = laps[laps["IsAccurate"]]

# Convert laptime to seconds
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# ========= SELECT TOP DRIVERS =========
drivers = (
    session.results
    .sort_values("Position")
    .head(TOP_N)["Abbreviation"]
    .tolist()
)

laps = laps[laps["Driver"].isin(drivers)]

# ========= CLEAN LAPS =========
laps = laps[
    laps["PitInTime"].isna() &
    laps["PitOutTime"].isna() &
    (laps["Compound"] == COMPOUND)
]

# ========= REMOVE OUTLIERS (IQR PER DRIVER PER STINT) =========
clean = []

for (d, stint), dl in laps.groupby(["Driver", "Stint"]):
    if len(dl) < 5:
        continue

    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1

    dl = dl[
        (dl["LapTimeSec"] >= q1 - 1.5 * iqr) &
        (dl["LapTimeSec"] <= q3 + 1.5 * iqr)
    ]

    clean.append(dl)

clean = pd.concat(clean)

# ========= PLOT TYRE DEGRADATION =========
plt.figure(figsize=(14,6))

for d in drivers:
    dl = clean[clean["Driver"] == d]

    # pilih stint terpanjang untuk driver tsb
    if dl.empty:
        continue

    stint_id = (
        dl.groupby("Stint").size().idxmax()
    )

    stint_laps = dl[dl["Stint"] == stint_id]

    if len(stint_laps) < 5:
        continue

    x = stint_laps["TyreLife"]
    y = stint_laps["LapTimeSec"]

    # Linear regression → degradation slope
    z = np.polyfit(x, y, 1)
    y_fit = np.polyval(z, x)

    plt.plot(x, y_fit, label=f"{d} ({z[0]:+.03f} s/lap)")

plt.title(f"Tyre Degradation – {COMPOUND}\n{GP} {YEAR}")
plt.xlabel("Lap on Tyre (TyreLife)")
plt.ylabel("Lap Time (s)")
plt.grid(alpha=0.3)
plt.legend(ncol=2)
plt.tight_layout()
plt.show()
