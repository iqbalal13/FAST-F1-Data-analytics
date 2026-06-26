import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# =============================
# CONFIG
# =============================
YEAR = 2026
GP = "Miami"
SESSION = "R"

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# =============================
# SETUP
# =============================
fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl()

plt.style.use("dark_background")

print("FastF1 Version:", fastf1.__version__)

# =============================
# LOAD SESSION
# =============================
session = fastf1.get_session(YEAR, GP, SESSION)

try:
    session.load()
except Exception as e:
    print("Load warning:", e)

# =============================
# VERIFY LAPS
# =============================
if not hasattr(session, "_laps"):
    raise RuntimeError(
        f"No lap data available for {GP} {YEAR} {SESSION}. "
        "FastF1 loaded session metadata but not timing data."
    )

laps = session.laps.copy()

# =============================
# CLEAN LAPS
# =============================
if "IsAccurate" in laps.columns:
    laps = laps[laps["IsAccurate"] == True]

laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()

# =============================
# RESULTS
# =============================
results = session.results.sort_values("Position")

drivers = results.head(10)["Abbreviation"].tolist()

laps = laps[laps["Driver"].isin(drivers)]

# =============================
# COLORS
# =============================
cmap = plt.colormaps["tab10"]

driver_colors = {
    drv: cmap(i % 10)
    for i, drv in enumerate(drivers)
}

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
plt.figure(figsize=(15, 7))

for drv in drivers:

    drv_laps = laps[laps["Driver"] == drv]

    if drv_laps.empty:
        continue

    plt.plot(
        drv_laps["LapNumber"],
        drv_laps["LapTimeSec"],
        label=drv,
        color=driver_colors[drv],
        linewidth=1.8
    )

    if "Compound" in drv_laps.columns:

        for compound, group in drv_laps.groupby("Compound"):

            plt.scatter(
                group["LapNumber"],
                group["LapTimeSec"],
                color=tyre_colors.get(compound, "gray"),
                s=35,
                edgecolors="black",
                zorder=3
            )

    if "PitInTime" in drv_laps.columns:

        pit_laps = drv_laps[drv_laps["PitInTime"].notna()]

        for lap in pit_laps["LapNumber"]:

            plt.axvline(
                lap,
                color=driver_colors[drv],
                linestyle="--",
                linewidth=1,
                alpha=0.25
            )

# =============================
# LABELS
# =============================
plt.title(
    f"Race Pace, Tyre & Pit Stop Analysis\n{GP} GP {YEAR}",
    fontsize=15
)

plt.xlabel("Lap Number")
plt.ylabel("Lap Time (seconds)")

plt.grid(alpha=0.25)

plt.legend(
    title="Drivers",
    ncol=5,
    fontsize=9
)

plt.tight_layout()
plt.show()
