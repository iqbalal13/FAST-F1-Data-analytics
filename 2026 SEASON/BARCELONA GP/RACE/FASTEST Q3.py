import os
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd

# ======================================================
# CACHE
# ======================================================
CACHE_DIR = "/content/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

fastf1.plotting.setup_mpl(misc_mpl_mods=False)

print("FastF1 Version:", fastf1.__version__)

# ======================================================
# CONFIG
# ======================================================
YEAR = 2026
RACE_NAME = "Catalunya"
SESSION = "Q"

# ======================================================
# LOAD SESSION
# ======================================================
session = fastf1.get_session(YEAR, RACE_NAME, SESSION)

try:
    session.load()
except Exception as e:
    print("Warning ketika load session:")
    print(e)

# ======================================================
# RESULTS
# ======================================================
results = session.results.copy()

if results.empty:
    raise ValueError("Session berhasil dimuat tetapi results kosong.")

results = results.dropna(subset=["Q3"])

results["Q3"] = pd.to_timedelta(results["Q3"])

pole_time = results["Q3"].min()

results["Delta"] = (
    results["Q3"] - pole_time
).dt.total_seconds()

results = results.sort_values("Delta")

# ======================================================
# TEAM COLORS (MANUAL)
# ======================================================
TEAM_COLORS = {

    "McLaren": "#FF8000",
    "Ferrari": "#DC0000",
    "Mercedes": "#00D2BE",
    "Red Bull": "#1E41FF",
    "Red Bull Racing": "#1E41FF",
    "Oracle Red Bull Racing": "#1E41FF",

    "Williams": "#005AFF",

    "Aston Martin": "#006F62",
    "Aston Martin Aramco": "#006F62",

    "Alpine": "#0090FF",
    "BWT Alpine": "#0090FF",

    "Kick Sauber": "#00E701",
    "Sauber": "#00E701",
    "Stake F1 Team Kick Sauber": "#00E701",

    "Haas": "#B6BABD",
    "Haas F1 Team": "#B6BABD",
    "MoneyGram Haas F1 Team": "#B6BABD",

    "Racing Bulls": "#6692FF",
    "Visa Cash App RB": "#6692FF",
    "Visa Cash App Racing Bulls": "#6692FF",

    "RB": "#6692FF"
}

colors = []

for team in results["TeamName"]:

    color = TEAM_COLORS.get(team)

    if color is None:
        print(f"Team belum dikenali: {team}")
        color = "#808080"

    colors.append(color)

# ======================================================
# DEBUG
# ======================================================
print(results[["Abbreviation", "TeamName"]])

print(colors)

# ======================================================
# PLOT
# ======================================================
plt.figure(figsize=(14,7))

bars = plt.bar(
    results["Abbreviation"],
    results["Delta"],
    color=colors,
    edgecolor="black",
    linewidth=1
)

plt.title(
    f"Delta to Pole - {RACE_NAME} {YEAR} Qualifying",
    fontsize=16
)

plt.xlabel("Driver", fontsize=12)
plt.ylabel("Delta to Pole (seconds)", fontsize=12)

plt.grid(axis="y", linestyle="--", alpha=0.4)

for bar, delta in zip(bars, results["Delta"]):

    plt.text(
        bar.get_x() + bar.get_width()/2,
        delta + 0.01,
        f"+{delta:.3f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()

plt.show()
