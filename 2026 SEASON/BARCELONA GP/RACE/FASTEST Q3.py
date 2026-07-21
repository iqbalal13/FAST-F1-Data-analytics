
import fastf1
import fastf1.plotting

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import os

# ==========================
# Cache
# ==========================
cache_dir = "cache"
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)

fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# ==========================
# Load Session
# ==========================
YEAR = 2026
ROUND = 7
SESSION = "Q"

session = fastf1.get_session(YEAR, ROUND, SESSION)
session.load()

# ==========================
# Prepare Data
# ==========================
results = session.results.copy()

results = (
    results
    .dropna(subset=["Q3"])
    .sort_values("Q3")
    .head(10)
)

pole_time = results.iloc[0]["Q3"]

results["Delta"] = (
    results["Q3"] - pole_time
).dt.total_seconds()

# ==========================
# Colors (P1-P10)
# ==========================
colors = [
    "#FFD700",  # Gold
    "#C0C0C0",  # Silver
    "#CD7F32",  # Bronze
    "#1F77B4",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F"
]

# ==========================
# Plot
# ==========================
fig, ax = plt.subplots(figsize=(11,7))

bars = ax.barh(
    results["Abbreviation"],
    results["Delta"],
    color=colors
)

ax.invert_yaxis()

for i, delta in enumerate(results["Delta"]):
    ax.text(
        delta + 0.01,
        i,
        f"+{delta:.3f}s",
        va="center",
        fontsize=10
    )

ax.set_xlabel("Delta to Pole (seconds)", fontsize=12)
ax.set_ylabel("Driver", fontsize=12)

ax.set_title(
    f"{session.event['EventName']} {YEAR}\nQualifying Q3 Delta (Top 10)",
    fontsize=15,
    weight="bold"
)

ax.grid(axis="x", linestyle="--", alpha=0.4)

legend_handles = [
    mpatches.Patch(color=colors[i], label=f"P{i+1}")
    for i in range(10)
]

ax.legend(
    handles=legend_handles,
    bbox_to_anchor=(1.02,1),
    loc="upper left"
)

plt.tight_layout()
plt.show()
