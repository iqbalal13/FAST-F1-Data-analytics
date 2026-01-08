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
GP = "Japan"
SESSION = "R"
CACHE_DIR = "cache"

# =============================
# SETUP (FIX CACHE ERROR)
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
# COLORS (VERSION-PROOF)
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
plt.figure(figsize=(15,7))

for drv in drivers:
    drv_laps = laps[laps["Driver"] == drv]

    # Race pace
    plt.plot(
        drv_laps["LapNumber"],
        drv_laps["LapTimeSec"],
        color=driver_colors[drv],
        linewidth=1.8,
        label=drv
    )

    # Tyre compound markers
    for compound, group in drv_laps.groupby("Compound"):
        plt.scatter(
            group["LapNumber"],
            group["LapTimeSec"],
            color=tyre_colors.get(compound, "gray"),
            s=35,
            edgecolors="black",
            zorder=3
        )

    # Pit stop markers
    pit_laps = drv_laps[drv_laps["PitInTime"].notna()]
    for lap in pit_laps["LapNumber"]:
        plt.axvline(
            lap,
            color=driver_colors[drv],
            linestyle="--",
            alpha=0.25,
            linewidth=1
        )

# =============================
# LABELS
# =============================
plt.title(
    "Race Pace, Tyre & Pit Stop Analysis – Top 10\nJapan GP 2025",
    fontsize=15
)
plt.xlabel("Lap Number")
plt.ylabel("Lap Time (seconds)")
plt.grid(alpha=0.25)
plt.legend(title="Drivers", ncol=5, fontsize=9)
plt.tight_layout()
plt.show()
