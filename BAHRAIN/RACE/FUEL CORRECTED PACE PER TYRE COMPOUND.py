import fastf1, os
import matplotlib.pyplot as plt
import pandas as pd

# ===== CONFIG =====
YEAR, GP, SESSION = 2025, "Bahrain Grand Prix", "R"
CACHE_DIR = "cache"

FUEL_START = 110
FUEL_BURN = 1.5
FUEL_PENALTY = 0.033

os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

# ===== LOAD SESSION =====
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

# ===== PLOT =====
tyre_colors = {"SOFT":"red","MEDIUM":"gold","HARD":"white"}

plt.figure(figsize=(15,6))

for comp, col in tyre_colors.items():
    cdata = clean[clean["Compound"] == comp]
    plt.scatter(
        cdata["LapNumber"],
        cdata["FuelCorrected"],
        color=col,
        alpha=0.7,
        s=30,
        label=comp
    )

plt.title("Fuel-Corrected Clean Pace per Tyre Compound\nBahrain GP 2025")
plt.xlabel("Lap")
plt.ylabel("Fuel-Corrected Lap Time (s)")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
