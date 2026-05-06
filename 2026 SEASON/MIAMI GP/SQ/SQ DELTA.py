import os
import shutil
import time
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# ===============================
# CONFIG
# ===============================
YEAR = 2026
RACE_NAME = "Miami Grand Prix"
SESSION_TYPE = "SQ"
MAX_RETRY = 3

CACHE_DIR = "/content/fastf1_cache"

# ===============================
# RESET CACHE
# ===============================
def reset_cache():
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

reset_cache()

fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# ===============================
# FIND EVENT
# ===============================
def get_event_by_name(year, race_name):
    schedule = fastf1.get_event_schedule(year)

    exact = schedule[schedule["EventName"] == race_name]
    if not exact.empty:
        return exact.iloc[0]

    contains = schedule[
        schedule["EventName"].str.contains(race_name, case=False, na=False)
    ]

    if not contains.empty:
        print(f"[INFO] Using closest match: {contains.iloc[0]['EventName']}")
        return contains.iloc[0]

    print("[WARNING] Race not found → latest race")
    return schedule.sort_values("RoundNumber").iloc[-1]

# ===============================
# LOAD SESSION
# ===============================
def load_session_safe(year, race_name, session_type):

    event = get_event_by_name(year, race_name)

    for i in range(MAX_RETRY):

        try:
            print(f"Loading: {event['EventName']} ({session_type})")

            session = fastf1.get_session(
                year,
                int(event["RoundNumber"]),
                session_type
            )

            session.load()

            print("SUCCESS\n")
            return session

        except Exception as e:
            print(f"Retry {i+1}/{MAX_RETRY} failed: {e}")
            time.sleep(2)

    raise RuntimeError("All retries failed!")

# ===============================
# LOAD
# ===============================
session = load_session_safe(YEAR, RACE_NAME, SESSION_TYPE)

# ===============================
# RESULTS
# ===============================
results = session.results.copy()

# 🔥 AUTO DETECT FINAL SESSION COLUMN
if "SQ3" in results.columns:
    final_col = "SQ3"
elif "Q3" in results.columns:
    final_col = "Q3"
else:
    raise RuntimeError("No SQ3/Q3 column found")

print(f"Using column: {final_col}")

# filter
results = results.dropna(subset=[final_col])

# convert timedelta
results[final_col] = pd.to_timedelta(results[final_col])

# ===============================
# DELTA TO POLE
# ===============================
pole_time = results[final_col].min()

results["Delta"] = (
    results[final_col] - pole_time
).dt.total_seconds()

results = results.sort_values("Delta").reset_index(drop=True)

# ===============================
# COLORS
# ===============================
n = len(results)

cmap = plt.get_cmap("turbo")

colors = [cmap(i / n) for i in range(n)]

# ===============================
# TEAM EDGE COLORS
# ===============================
edge_colors = []

for team in results["TeamName"]:

    try:
        edge_colors.append(
            fastf1.plotting.get_team_color(team, session)
        )

    except:
        edge_colors.append("black")

# ===============================
# PLOT
# ===============================
plt.figure(figsize=(14, 7))

plt.bar(
    results["Abbreviation"],
    results["Delta"],
    color=colors,
    edgecolor=edge_colors,
    linewidth=2
)

plt.title(
    f"Delta to Pole Sprint – {session.event['EventName']} {session.event.year}",
    fontsize=16
)

plt.xlabel("Driver")
plt.ylabel("Delta to Pole (seconds)")

plt.grid(axis="y", linestyle="--", alpha=0.5)

# annotate
for i, delta in enumerate(results["Delta"]):

    plt.text(
        i,
        delta + 0.01,
        f"+{delta:.3f}",
        ha="center",
        fontsize=9
    )

plt.tight_layout()
plt.show()
