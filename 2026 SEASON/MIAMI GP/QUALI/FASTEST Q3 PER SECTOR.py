import os
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt

# ===============================
# CACHE
# ===============================
CACHE_DIR = "/content/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

fastf1.Cache.enable_cache(CACHE_DIR)
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# ===============================
# CONFIG
# ===============================
YEAR = 2026
RACE_NAME = "Miami Grand Prix"
SESSION = "Q"

# ===============================
# LOAD SESSION
# ===============================
session = fastf1.get_session(YEAR, RACE_NAME, SESSION)
session.load(laps=True)

# ===============================
# FILTER Q3
# ===============================
laps = session.laps.copy()

q3_drivers = session.results.dropna(subset=["Q3"])["Abbreviation"]

laps = laps[laps["Driver"].isin(q3_drivers)]

laps = laps.pick_quicklaps()

laps = laps[
    laps["Sector1Time"].notna() &
    laps["Sector2Time"].notna() &
    laps["Sector3Time"].notna()
]

# ===============================
# FASTEST DRIVER PER SECTOR
# ===============================
lap_s1 = laps.loc[laps["Sector1Time"].idxmin()]
lap_s2 = laps.loc[laps["Sector2Time"].idxmin()]
lap_s3 = laps.loc[laps["Sector3Time"].idxmin()]

driver_s1 = lap_s1["Driver"]
driver_s2 = lap_s2["Driver"]
driver_s3 = lap_s3["Driver"]

print("S1 Fastest:", driver_s1)
print("S2 Fastest:", driver_s2)
print("S3 Fastest:", driver_s3)

# ===============================
# AUTO DRIVER COLORS
# ===============================
base_colors = [
    "red",
    "deepskyblue",
    "gold",
    "lime",
    "magenta",
    "orange"
]

unique_drivers = []

for drv in [driver_s1, driver_s2, driver_s3]:
    if drv not in unique_drivers:
        unique_drivers.append(drv)

driver_colors = {
    drv: base_colors[i]
    for i, drv in enumerate(unique_drivers)
}

# ===============================
# REFERENCE LAP
# ===============================
pole_lap = laps.loc[laps["LapTime"].idxmin()]

pos = pole_lap.get_pos_data().copy()

pos["TimeSec"] = pos["Time"].dt.total_seconds()

# ===============================
# SECTOR SPLIT
# ===============================
s1_end = pole_lap["Sector1Time"].total_seconds()

s2_end = (
    pole_lap["Sector1Time"].total_seconds()
    + pole_lap["Sector2Time"].total_seconds()
)

sector1 = pos[pos["TimeSec"] <= s1_end]

sector2 = pos[
    (pos["TimeSec"] > s1_end) &
    (pos["TimeSec"] <= s2_end)
]

sector3 = pos[pos["TimeSec"] > s2_end]

# ===============================
# PLOT
# ===============================
plt.figure(figsize=(8, 8))

ax = plt.gca()
ax.set_facecolor("#1f1f1f")

# S1
plt.plot(
    sector1["X"],
    sector1["Y"],
    color=driver_colors[driver_s1],
    linewidth=5,
    label=f"S1 Fastest – {driver_s1}"
)

# S2
plt.plot(
    sector2["X"],
    sector2["Y"],
    color=driver_colors[driver_s2],
    linewidth=5,
    label=f"S2 Fastest – {driver_s2}"
)

# S3
plt.plot(
    sector3["X"],
    sector3["Y"],
    color=driver_colors[driver_s3],
    linewidth=5,
    label=f"S3 Fastest – {driver_s3}"
)

plt.title(
    f"Fastest Q3 Sectors by Driver\n{session.event['EventName']} {session.event.year}",
    fontsize=14,
    color="white"
)

plt.axis("off")

plt.legend(
    facecolor="#2b2b2b",
    edgecolor="none",
    labelcolor="white"
)

plt.tight_layout()
plt.show()
