# ================================================================
# SEPANG 2026 — TOP 10 GAP EVOLUTION
# Gap to Race Leader at End of Each Lap
# OPENF1 / GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ================================================================
# CONFIG
# ================================================================

YEAR = 2026
BASE = "https://api.openf1.org/v1"


# ================================================================
# HELPERS
# ================================================================

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

        raise RuntimeError(
            f"OpenF1 HTTP {r.status_code}"
        )

    data = r.json()

    if not data and not allow_empty:

        raise RuntimeError(
            f"No data from {endpoint}"
        )

    return data


def parse_dt(x):

    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


# ================================================================
# 1. FIND SEPANG RACE
# ================================================================

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


sepang_mask = (

    location.astype(str).str.contains(
        "Kuala Lumpur|Sepang",
        case=False,
        regex=True,
        na=False
    )

    |

    circuit.astype(str).str.contains(
        "Kuala Lumpur|Sepang",
        case=False,
        regex=True,
        na=False
    )
)


sepang = sessions[
    sepang_mask
].copy()


race_sessions = sepang[

    sepang["session_name"]
    .astype(str)
    .str.lower()
    .eq("race")

].copy()


if race_sessions.empty:

    raise RuntimeError(
        "Sepang race tidak ditemukan."
    )


race_sessions["dt"] = parse_dt(
    race_sessions["date_start"]
)


session = (
    race_sessions
    .sort_values("dt")
    .iloc[-1]
)


SESSION_KEY = int(
    session["session_key"]
)


print("=" * 70)
print("SEPANG RACE")
print("=" * 70)

print("Session Key :", SESSION_KEY)
print("Location    :", session["location"])
print("Circuit     :", session["circuit_short_name"])


# ================================================================
# 2. DRIVERS
# ================================================================

drivers = pd.DataFrame(
    api_get(
        "drivers",
        {
            "session_key":
                SESSION_KEY
        }
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
    drivers["driver_number"]
    .astype(int)
)


drivers = drivers.drop_duplicates(
    "driver_number"
)


driver_map = (

    drivers
    .set_index("driver_number")
    ["name_acronym"]
    .to_dict()

)


# ================================================================
# 3. TOP 10 FINAL RESULT
# ================================================================

results = pd.DataFrame(
    api_get(
        "session_result",
        {
            "session_key":
                SESSION_KEY
        }
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


top10 = results[

    results["position"]
    .between(1, 10)

].copy()


top10 = top10.sort_values(
    "position"
)


top10["driver_number"] = (
    top10["driver_number"]
    .astype(int)
)


top10["Driver"] = (

    top10["driver_number"]
    .map(driver_map)

)


top10["Driver"] = (
    top10["Driver"]
    .fillna(
        top10["driver_number"].astype(str)
    )
)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


print("\nTOP 10:")
display(
    top10[
        [
            "position",
            "Driver",
            "driver_number"
        ]
    ]
)


# ================================================================
# 4. LOAD LAPS
# ================================================================

laps = pd.DataFrame(
    api_get(
        "laps",
        {
            "session_key":
                SESSION_KEY
        }
    )
)


for col in [
    "driver_number",
    "lap_number",
    "lap_duration"
]:

    laps[col] = pd.to_numeric(
        laps[col],
        errors="coerce"
    )


laps["date_start_parsed"] = parse_dt(
    laps["date_start"]
)


laps = laps[
    laps["driver_number"].isin(
        TOP10
    )
].copy()


laps = laps.dropna(
    subset=[
        "date_start_parsed",
        "lap_number",
        "lap_duration"
    ]
)


# estimate finish timestamp of each lap

laps["lap_end"] = (

    laps["date_start_parsed"]

    +

    pd.to_timedelta(
        laps["lap_duration"],
        unit="s"
    )

)


# ================================================================
# 5. LOAD INTERVAL DATA
# ================================================================

print("\nLoading interval data...")


intervals = pd.DataFrame(
    api_get(
        "intervals",
        {
            "session_key":
                SESSION_KEY
        }
    )
)


intervals["driver_number"] = pd.to_numeric(
    intervals["driver_number"],
    errors="coerce"
)


intervals["date_parsed"] = parse_dt(
    intervals["date"]
)


intervals = intervals[
    intervals["driver_number"].isin(
        TOP10
    )
].copy()


# keep original raw gap
intervals["gap_raw"] = (
    intervals["gap_to_leader"]
)


# numeric seconds
# "+1 LAP" etc becomes NaN

intervals["gap_seconds"] = pd.to_numeric(
    intervals["gap_to_leader"],
    errors="coerce"
)


# ================================================================
# 6. SAMPLE GAP AT END OF EVERY LAP
# ================================================================

gap_frames = []


for _, result_row in top10.iterrows():

    driver_num = int(
        result_row["driver_number"]
    )

    driver = result_row["Driver"]

    position = int(
        result_row["position"]
    )


    dlaps = laps[

        laps["driver_number"]
        ==
        driver_num

    ][
        [
            "lap_number",
            "lap_end"
        ]
    ].copy()


    dint = intervals[

        intervals["driver_number"]
        ==
        driver_num

    ][
        [
            "date_parsed",
            "gap_raw",
            "gap_seconds"
        ]
    ].copy()


    dlaps = dlaps.sort_values(
        "lap_end"
    )

    dint = dint.sort_values(
        "date_parsed"
    )


    if dlaps.empty or dint.empty:
        continue


    # nearest interval sample to end of lap

    merged = pd.merge_asof(

        dlaps,

        dint,

        left_on="lap_end",

        right_on="date_parsed",

        direction="nearest",

        tolerance=pd.Timedelta(
            seconds=10
        )

    )


    # If a valid interval row exists but gap is null,
    # that means the car was the current race leader.

    leader_mask = (

        merged["date_parsed"].notna()

        &

        merged["gap_raw"].isna()

    )


    merged.loc[
        leader_mask,
        "gap_seconds"
    ] = 0.0


    merged["Driver"] = driver

    merged["FinishPosition"] = position

    merged["driver_number"] = driver_num


    gap_frames.append(
        merged
    )


if not gap_frames:

    raise RuntimeError(
        "Tidak berhasil membuat gap evolution."
    )


gap_laps = pd.concat(
    gap_frames,
    ignore_index=True
)


# ================================================================
# 7. DISPLAY SAMPLE TABLE
# ================================================================

print("\n" + "=" * 70)
print("LAP-BY-LAP GAP SAMPLE")
print("=" * 70)


display(
    gap_laps[
        [
            "lap_number",
            "FinishPosition",
            "Driver",
            "gap_seconds"
        ]
    ].sort_values(
        [
            "lap_number",
            "FinishPosition"
        ]
    )
)


# ================================================================
# 8. PLOT GAP EVOLUTION
# ================================================================

fig, ax = plt.subplots(
    figsize=(17, 9)
)


cmap = plt.colormaps["tab10"]


for i, (_, result_row) in enumerate(
    top10.iterrows()
):

    driver = result_row["Driver"]

    position = int(
        result_row["position"]
    )


    d = gap_laps[

        gap_laps["Driver"]
        ==
        driver

    ].sort_values(
        "lap_number"
    )


    # only numeric gaps
    d = d[
        d["gap_seconds"].notna()
    ]


    if d.empty:
        continue


    ax.plot(

        d["lap_number"],

        d["gap_seconds"],

        linewidth=2.2,

        marker="o",

        markersize=2.5,

        color=cmap(i),

        label=f"P{position} {driver}"

    )


# ================================================================
# STYLE
# ================================================================

ax.axhline(
    0,
    linewidth=1,
    alpha=0.5
)


ax.set_title(

    "SEPANG 2026 — TOP 10 GAP EVOLUTION\n"
    "Gap to Race Leader at End of Each Lap",

    fontsize=17,

    fontweight="bold",

    pad=18

)


ax.set_xlabel(
    "Race Lap",
    fontsize=12
)


ax.set_ylabel(
    "Gap to Leader (seconds)",
    fontsize=12
)


ax.grid(
    linestyle="--",
    alpha=0.25
)


ax.legend(
    ncol=5,
    fontsize=9,
    loc="upper left"
)


ax.set_xlim(
    left=1
)


# 0 sec di bawah
ax.set_ylim(
    bottom=0
)


plt.tight_layout()
plt.show()
