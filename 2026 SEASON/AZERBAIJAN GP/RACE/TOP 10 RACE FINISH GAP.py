# ============================================================
# F1 2026 AZERBAIJAN GP - BAKU
# TOP 10 RACE FINISH GAP
# LOWER BAR = BETTER / CLOSER TO WINNER
# OPENF1 - GOOGLE COLAB - ONE CELL
# ============================================================

!pip install -q requests pandas numpy matplotlib

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

YEAR = 2026
BASE = "https://api.openf1.org/v1"


# ------------------------------------------------------------
# API helper
# ------------------------------------------------------------
def api_get(endpoint, params=None, allow_empty=False):
    r = requests.get(
        f"{BASE}/{endpoint}",
        params=params,
        timeout=90,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    )

    if r.status_code != 200:
        print("URL    :", r.url)
        print("Status :", r.status_code)
        print("Body   :", r.text[:500])
        raise RuntimeError(f"OpenF1 HTTP {r.status_code}")

    data = r.json()

    if not data and not allow_empty:
        raise RuntimeError(f"No data returned from {endpoint}")

    return data


def parse_dt(x):
    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


# ------------------------------------------------------------
# Cari race Azerbaijan / Baku
# ------------------------------------------------------------
sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)

location = (
    sessions["location"]
    if "location" in sessions.columns
    else pd.Series("", index=sessions.index)
)

circuit = (
    sessions["circuit_short_name"]
    if "circuit_short_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)

baku_mask = (
    location.astype(str).str.contains(
        "Baku|Azerbaijan",
        case=False,
        regex=True,
        na=False
    )
    |
    circuit.astype(str).str.contains(
        "Baku|Azerbaijan",
        case=False,
        regex=True,
        na=False
    )
)

baku = sessions[baku_mask].copy()

race_sessions = baku[
    baku["session_name"].astype(str).str.lower().eq("race")
].copy()

if race_sessions.empty:
    raise RuntimeError("Race Azerbaijan / Baku 2026 tidak ditemukan.")

race_sessions["parsed_start"] = parse_dt(
    race_sessions["date_start"]
)

session = (
    race_sessions
    .sort_values("parsed_start")
    .iloc[-1]
)

SESSION_KEY = int(
    session["session_key"]
)

print("=" * 75)
print("2026 AZERBAIJAN GRAND PRIX")
print("BAKU CITY CIRCUIT")
print("=" * 75)
print("Session Key :", SESSION_KEY)
print("Location    :", session.get("location", "Baku"))
print("Circuit     :", session.get("circuit_short_name", "Baku"))
print()


# ------------------------------------------------------------
# Driver names
# ------------------------------------------------------------
drivers = pd.DataFrame(
    api_get(
        "drivers",
        {"session_key": SESSION_KEY}
    )
)

drivers["driver_number"] = pd.to_numeric(
    drivers["driver_number"],
    errors="coerce"
)

drivers = drivers.dropna(
    subset=["driver_number"]
)

drivers["driver_number"] = (
    drivers["driver_number"].astype(int)
)

drivers = drivers.drop_duplicates(
    "driver_number"
)

driver_acronym = (
    drivers
    .set_index("driver_number")["name_acronym"]
    .to_dict()
)

driver_full_name = (
    drivers
    .set_index("driver_number")["full_name"]
    .to_dict()
)

team_map = (
    drivers
    .set_index("driver_number")["team_name"]
    .to_dict()
    if "team_name" in drivers.columns
    else {}
)


# ------------------------------------------------------------
# Official race result dari OpenF1
# ------------------------------------------------------------
results = pd.DataFrame(
    api_get(
        "session_result",
        {"session_key": SESSION_KEY}
    )
)

results["position"] = pd.to_numeric(
    results["position"],
    errors="coerce"
)

results["driver_number"] = pd.to_numeric(
    results["driver_number"],
    errors="coerce"
)

top10 = (
    results[
        results["position"].between(1, 10)
    ]
    .sort_values("position")
    .copy()
)

top10["driver_number"] = (
    top10["driver_number"].astype(int)
)

top10["Driver"] = (
    top10["driver_number"].map(driver_acronym)
)

top10["Name"] = (
    top10["driver_number"].map(driver_full_name)
)

top10["Team"] = (
    top10["driver_number"].map(team_map)
)

# gap_to_leader bisa numeric atau "+N LAP(S)"
top10["GapRaw"] = top10["gap_to_leader"]
top10["GapSeconds"] = pd.to_numeric(
    top10["gap_to_leader"],
    errors="coerce"
)

# P1 selalu 0
top10.loc[
    top10["position"] == 1,
    "GapSeconds"
] = 0.0


# ------------------------------------------------------------
# Tabel
# ------------------------------------------------------------
display_df = top10[
    [
        "position",
        "Driver",
        "Name",
        "Team",
        "GapRaw"
    ]
].copy()

display_df = display_df.rename(
    columns={
        "position": "Position",
        "GapRaw": "Gap to Winner"
    }
)

display_df["Position"] = (
    display_df["Position"].astype(int)
)

print("TOP 10 RACE RESULT")
display(display_df)


# ------------------------------------------------------------
# Print result
# ------------------------------------------------------------
for _, row in top10.iterrows():

    pos = int(row["position"])

    if pos == 1:
        gap_text = "WINNER"
    elif pd.notna(row["GapSeconds"]):
        gap_text = f"+{row['GapSeconds']:.3f}s"
    else:
        gap_text = str(row["GapRaw"])

    print(
        f"P{pos:02d} | "
        f"{row['Driver']:<3} | "
        f"{str(row['Name']):<22} | "
        f"{gap_text}"
    )


# ------------------------------------------------------------
# Grafik
# ------------------------------------------------------------
plot_df = top10[
    top10["GapSeconds"].notna()
].copy()

cmap = plt.colormaps["tab10"]

driver_colors = {
    driver: cmap(i)
    for i, driver in enumerate(plot_df["Driver"].tolist())
}

colors = [
    driver_colors[driver]
    for driver in plot_df["Driver"]
]

fig, ax = plt.subplots(
    figsize=(13, 7)
)

bars = ax.bar(
    plot_df["Driver"],
    plot_df["GapSeconds"],
    color=colors,
    width=0.7
)

for bar, (_, row) in zip(
    bars,
    plot_df.iterrows()
):
    height = bar.get_height()
    pos = int(row["position"])

    if pos == 1:
        label = "P1\nWINNER\n0.000s"
        y_position = 0.35
    else:
        label = (
            f"P{pos}\n"
            f"+{row['GapSeconds']:.3f}s"
        )
        y_position = height + 0.35

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        y_position,
        label,
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold"
    )

ax.set_title(
    "2026 Azerbaijan GP — Top 10 Race Finish\n"
    "Gap to Winner (Lower = Better)",
    fontsize=16,
    fontweight="bold",
    pad=20
)

ax.set_xlabel("Driver")
ax.set_ylabel("Seconds Behind Winner")
ax.set_ylim(
    0,
    plot_df["GapSeconds"].max() + 5
)
ax.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.show()
