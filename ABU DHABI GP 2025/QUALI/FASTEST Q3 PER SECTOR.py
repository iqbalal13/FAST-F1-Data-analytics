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
YEAR = 2025
RACE_NAME = "Abu Dhabi"
SESSION = "Q"

# ===============================
# LOAD SESSION
# ===============================
session = fastf1.get_session(YEAR, RACE_NAME, SESSION)
session.load()

# ===============================
# FILTER LAPS WITH VALID SECTORS
# ===============================
laps = session.laps
laps = laps[
    laps["Sector1Time"].notna() &
    laps["Sector2Time"].notna() &
    laps["Sector3Time"].notna()
]

# ===============================
# FASTEST SECTOR LAPS
# ===============================
lap_s1 = laps.loc[laps["Sector1Time"].idxmin()]
lap_s2 = laps.loc[laps["Sector2Time"].idxmin()]
lap_s3 = laps.loc[laps["Sector3Time"].idxmin()]

# ===============================
# CUT TELEMETRY BY TIME
# ===============================
def cut_sector_telemetry(lap, t_start, t_end):
    tel = lap.get_telemetry().copy()
    tel["TimeSec"] = tel["Time"].dt.total_seconds()
    return tel[(tel["TimeSec"] >= t_start) & (tel["TimeSec"] <= t_end)]

# sektor timing
s1_end = lap_s1["Sector1Time"].total_seconds()

s2_start = lap_s2["Sector1Time"].total_seconds()
s2_end   = s2_start + lap_s2["Sector2Time"].total_seconds()

s3_start = lap_s3["Sector1Time"].total_seconds() + lap_s3["Sector2Time"].total_seconds()
s3_end   = lap_s3["LapTime"].total_seconds()

# potong telemetry
tel_s1 = cut_sector_telemetry(lap_s1, 0.0, s1_end)
tel_s2 = cut_sector_telemetry(lap_s2, s2_start, s2_end)
tel_s3 = cut_sector_telemetry(lap_s3, s3_start, s3_end)

# ===============================
# DRIVER-BASED COLORS (FIX)
# ===============================
DRIVER_COLORS = {
    lap_s1["Driver"]: "gold",
    lap_s2["Driver"]: "deepskyblue",
    lap_s3["Driver"]: "red"
}

# ===============================
# PLOT
# ===============================
plt.figure(figsize=(8, 8))
ax = plt.gca()
ax.set_facecolor("#1f1f1f")

plt.plot(tel_s1["X"], tel_s1["Y"],
         color=DRIVER_COLORS[lap_s1["Driver"]],
         linewidth=4,
         label=f"Sektor 1 – {lap_s1['Driver']}")

plt.plot(tel_s2["X"], tel_s2["Y"],
         color=DRIVER_COLORS[lap_s2["Driver"]],
         linewidth=4,
         label=f"Sektor 2 – {lap_s2['Driver']}")

plt.plot(tel_s3["X"], tel_s3["Y"],
         color=DRIVER_COLORS[lap_s3["Driver"]],
         linewidth=4,
         label=f"Sektor 3 – {lap_s3['Driver']}")

plt.title(
    "Fastest Sector Map (Driver-Based Colors)\nAbu Dhabi GP 2025 – Qualifying",
    fontsize=14, color="white"
)

plt.axis("off")
plt.legend(facecolor="#2b2b2b", edgecolor="none", labelcolor="white")
plt.tight_layout()
plt.show()
