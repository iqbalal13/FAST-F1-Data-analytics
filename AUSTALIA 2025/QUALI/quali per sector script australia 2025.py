import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt

fastf1.Cache.enable_cache("cache")
fastf1.plotting.setup_mpl()

session = fastf1.get_session(2025, "Australian Grand Prix", "Q")
session.load()

laps = session.laps.pick_quicklaps()
laps = laps[laps["IsAccurate"] == True]

# Q3 ≈ lap-lap terakhir
q3_laps = laps.sort_values("LapStartTime").tail(10)

s1 = q3_laps.loc[q3_laps["Sector1Time"].idxmin()]
s2 = q3_laps.loc[q3_laps["Sector2Time"].idxmin()]
s3 = q3_laps.loc[q3_laps["Sector3Time"].idxmin()]

def get_xy(lap):
    tel = lap.get_telemetry()
    return tel["X"], tel["Y"]

x1, y1 = get_xy(s1)
x2, y2 = get_xy(s2)
x3, y3 = get_xy(s3)

plt.figure(figsize=(6,12))
plt.plot(x1, y1, linewidth=5, label=f"S1 – {s1.Driver}")
plt.plot(x2, y2, linewidth=5, label=f"S2 – {s2.Driver}")
plt.plot(x3, y3, linewidth=5, label=f"S3 – {s3.Driver}")

plt.title("Fastest Q3 Sector – Australian GP 2025")
plt.axis("off")
plt.legend()
plt.show()
