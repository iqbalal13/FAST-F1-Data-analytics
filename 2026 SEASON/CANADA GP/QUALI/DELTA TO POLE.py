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
RACE_NAME = "Canadian"
SESSION_TYPE = "Q"
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
# FIND EVENT (ROBUST)
# ===============================
def get_event_by_name(year, race_name):
    schedule = fastf1.get_event_schedule(year)

    # exact match
    exact = schedule[schedule["EventName"] == race_name]
    if not exact.empty:
        return exact.iloc[0]

    # fallback: contains
    contains = schedule[schedule["EventName"].str.contains(race_name, case=False, na=False)]
    if not contains.empty:
        print(f"[INFO] Using closest match: {contains.iloc[0]['EventName']}")
        return contains.iloc[0]

    # fallback terakhir
    print("[WARNING] Race name not found → using latest race")
    return schedule.sort_values("RoundNumber").iloc[-1]

# ===============================
# LOAD SESSION WITH RETRY
# ===============================
def load_session_safe(year, race_name, session_type):
    event = get_event_by_name(year, race_name)

    for i in range(MAX_RETRY):
        try:
            print(f"Loading: {event['EventName']} ({session_type})")

            session = fastf1.get_session(year, int(event["RoundNumber"]), session_type)
            session.load()

            print("SUCCESS\n")
            return session

        except Exception as e:
            print(f"Retry {i+1}/{MAX_RETRY} failed: {e}")
            time.sleep(3)

    raise Exception("All retries failed!")

# ===============================
# LOAD
# ===============================
session = load_session_safe(YEAR, RACE_NAME, SESSION_TYPE)

# ===============================
# RESULTS (Q3 ONLY)
# ===============================
results = session.results.copy()
results = results.dropna(subset=["Q3"])
results["Q3"] = pd.to_timedelta(results["Q3"])

# ===============================
# DELTA TO POLE
# ===============================
pole_time = results["Q3"].min()
results["Delta"] = (results["Q3"] - pole_time).dt.total_seconds()
results = results.sort_values("Delta").reset_index(drop=True)

# ===============================
# DRIVER UNIQUE COLORS (AUTO)
# ===============================
n = len(results)

# pilihan colormap: "tab20", "viridis", "plasma", "turbo"
cmap = plt.get_cmap("turbo")

colors = [cmap(i / n) for i in range(n)]

# ===============================
# OPTIONAL: TEAM EDGE COLOR
# ===============================
edge_colors = []
for team in results["TeamName"]:
    try:
        edge_colors.append(fastf1.plotting.get_team_color(team, session))
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

title = f"Delta to Pole – {session.event['EventName']} {session.event.year}"
plt.title(title, fontsize=16)

plt.xlabel("Driver")
plt.ylabel("Delta to Pole (seconds)")
plt.grid(axis="y", linestyle="--", alpha=0.5)

# annotate delta
for i, delta in enumerate(results["Delta"]):
    plt.text(i, delta + 0.01, f"+{delta:.3f}", ha="center", fontsize=9)

plt.tight_layout()
plt.show()
