import os
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd

# ===============================
# CACHE (WAJIB DI COLAB)
# ===============================
CACHE_DIR = "/content/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# ===============================
# CONFIG
# ===============================
YEAR = 2025
RACE_NAME = "Dutch"
SESSION = "Q"

# ===============================
# LOAD SESSION
# ===============================
session = fastf1.get_session(YEAR, RACE_NAME, SESSION)
session.load()

# ===============================
# OFFICIAL QUALI RESULTS (STABLE)
# ===============================
results = session.results.copy()

# Driver yang masuk Q3
results = results.dropna(subset=["Q3"])
results["Q3"] = pd.to_timedelta(results["Q3"])

# ===============================
# DELTA TO POLE
# ===============================
pole_time = results["Q3"].min()
results["Delta"] = (results["Q3"] - pole_time).dt.total_seconds()
results = results.sort_values("Delta")

# ===============================
# TEAM COLORS (FASTF1 3.7 – CORRECT)
# ===============================
colors = [
    fastf1.plotting.get_team_color(team, session)
    for team in results["TeamName"]
]

# ===============================
# PLOT
# ===============================
plt.figure(figsize=(14, 7))
plt.bar(
    results["Abbreviation"],
    results["Delta"],
    color=colors,
    edgecolor="black"
)

plt.title("Delta to Pole – Qualifying\nDutch GP 2025", fontsize=16)
plt.xlabel("Driver")
plt.ylabel("Delta to Pole (seconds)")
plt.grid(axis="y", linestyle="--", alpha=0.5)

for i, delta in enumerate(results["Delta"]):
    plt.text(i, delta + 0.01, f"+{delta:.3f}", ha="center", fontsize=9)

plt.tight_layout()
plt.show()
