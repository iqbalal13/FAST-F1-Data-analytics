import fastf1, os
import matplotlib.pyplot as plt
import pandas as pd

# ===== CONFIG =====
YEAR, GP, SESSION = 2025, "Bahrain Grand Prix", "R"
CACHE_DIR = "cache"

os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

laps = session.laps
laps = laps[laps["IsAccurate"]].copy()
laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

drivers = (
    session.results.sort_values("Position")
    .head(10)["Abbreviation"]
    .tolist()
)

laps = laps[laps["Driver"].isin(drivers)]
laps = laps[laps["PitInTime"].isna() & laps["PitOutTime"].isna()]

# Outlier removal
clean = []
for d in drivers:
    dl = laps[laps["Driver"] == d]
    q1, q3 = dl["LapTimeSec"].quantile([0.25, 0.75])
    iqr = q3 - q1
    clean.append(dl[(dl["LapTimeSec"] >= q1-1.5*iqr) & (dl["LapTimeSec"] <= q3+1.5*iqr)])

clean = pd.concat(clean)

tyre_colors = {"SOFT":"red","MEDIUM":"gold","HARD":"white"}

plt.figure(figsize=(15,6))

for comp,col in tyre_colors.items():
    cdata = clean[clean["Compound"] == comp]
    plt.scatter(
        cdata["LapNumber"],
        cdata["LapTimeSec"],
        color=col,
        label=comp,
        alpha=0.7,
        s=30
    )

plt.title("Tyre Compound–Specific Clean Race Pace\nBahrain GP 2025")
plt.xlabel("Lap")
plt.ylabel("Lap Time (s)")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
