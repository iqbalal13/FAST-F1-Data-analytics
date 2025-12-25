import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import numpy as np

# =============================
# SETUP
# =============================
fastf1.Cache.enable_cache("cache")
fastf1.plotting.setup_mpl()

session = fastf1.get_session(2025, "Australian Grand Prix", "Q")
session.load()

laps = session.laps.pick_quicklaps()
laps = laps[laps["IsAccurate"] == True]

# =============================
# Q3 LAPS
# =============================
q3_laps = laps.sort_values("LapStartTime").tail(30)

# =============================
# FASTEST Q3 LAP PER DRIVER
# =============================
fastest_q3 = (
    q3_laps
    .groupby("Driver")
    .apply(lambda x: x.loc[x["LapTime"].idxmin()])
    .reset_index(drop=True)
)

top10 = fastest_q3.sort_values("LapTime").head(10).copy()
top10["LapTimeSeconds"] = top10["LapTime"].dt.total_seconds()

pole_time = top10["LapTimeSeconds"].min()
top10["DeltaToPole"] = top10["LapTimeSeconds"] - pole_time
top10 = top10.sort_values("DeltaToPole")

# =============================
# COLORS (AUTOMATIC)
# =============================
colors = plt.cm.tab10(np.linspace(0, 1, len(top10)))

# =============================
# PLOT
# =============================
plt.figure(figsize=(10,5))
plt.bar(
    top10["Driver"],
    top10["DeltaToPole"],
    color=colors
)

plt.title("Top 10 Q3 – Delta to Pole\nAustralian GP 2025", fontsize=14)
plt.ylabel("Delta to Pole (seconds)")
plt.xlabel("Driver")
plt.axhline(0, linewidth=1)
plt.tight_layout()
plt.show()

