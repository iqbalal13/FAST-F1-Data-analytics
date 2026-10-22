# ================================================================
# MADRID GP 2026 — MADRING
# TOP 10 GAP EVOLUTION
# Gap to Race Leader at End of Each Lap
#
# OPENF1
# GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time
import random
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ================================================================
# CONFIG
# ================================================================

YEAR = 2026
BASE = "https://api.openf1.org/v1"

LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 1.20


# ================================================================
# HTTP SESSION
# ================================================================

http = requests.Session()

http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})


# ================================================================
# RATE-LIMIT SAFE API
# ================================================================

def api_get(
    endpoint,
    params=None,
    allow_empty=False,
    max_retries=10
):

    global LAST_REQUEST_TIME

    url = f"{BASE}/{endpoint}"

    for attempt in range(max_retries):

        elapsed = time.time() - LAST_REQUEST_TIME

        if elapsed < MIN_REQUEST_INTERVAL:

            time.sleep(
                MIN_REQUEST_INTERVAL - elapsed
            )


        try:

            r = http.get(
                url,
                params=params,
                timeout=90
            )

            LAST_REQUEST_TIME = time.time()


        except requests.RequestException as e:

            wait = min(
                3 + attempt * 3,
                30
            )

            print(
                f"Network error [{endpoint}]: {e}"
            )

            print(
                f"Retry dalam {wait}s..."
            )

            time.sleep(wait)

            continue


        # --------------------------------------------------------
        # HTTP 429
        # --------------------------------------------------------

        if r.status_code == 429:

            retry_after = r.headers.get(
                "Retry-After"
            )

            if retry_after:

                try:
                    wait = float(retry_after)

                except:
                    wait = min(
                        4 + attempt * 4,
                        35
                    )

            else:

                wait = min(
                    4 + attempt * 4,
                    35
                )


            wait += random.uniform(
                0.3,
                1.0
            )


            print(
                f"⚠️ 429 on {endpoint}. "
                f"Retry {attempt+1}/{max_retries} "
                f"dalam {wait:.1f}s..."
            )


            time.sleep(wait)

            continue


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
                f"No data returned from {endpoint}"
            )


        return data


    raise RuntimeError(
        f"OpenF1 failed after "
        f"{max_retries} retries: {endpoint}"
    )


# ================================================================
# DATETIME
# ================================================================

def parse_dt(x):

    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


# ================================================================
# 1. FIND MADRID / MADRING RACE
# ================================================================

print("=" * 80)
print("MADRID GP 2026 — GAP EVOLUTION")
print("=" * 80)


sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)


location_col = (
    sessions["location"]
    if "location" in sessions.columns
    else pd.Series("", index=sessions.index)
)


circuit_col = (
    sessions["circuit_short_name"]
    if "circuit_short_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)


meeting_col = (
    sessions["meeting_name"]
    if "meeting_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)


madrid_mask = (

    location_col.astype(str).str.contains(
        "Madrid|Madring",
        case=False,
        regex=True,
        na=False
    )

    |

    circuit_col.astype(str).str.contains(
        "Madrid|Madring",
        case=False,
        regex=True,
        na=False
    )

    |

    meeting_col.astype(str).str.contains(
        "Madrid",
        case=False,
        na=False
    )
)


madrid = sessions[
    madrid_mask
].copy()


print("\nMadrid sessions found:")

show_cols = [
    c for c in [
        "session_key",
        "session_name",
        "meeting_name",
        "country_name",
        "location",
        "circuit_short_name",
        "date_start"
    ]
    if c in madrid.columns
]

display(
    madrid[show_cols]
)


race_sessions = madrid[

    madrid["session_name"]
    .astype(str)
    .str.lower()
    .eq("race")

].copy()


if race_sessions.empty:

    raise RuntimeError(
        "Madrid / Madring 2026 race tidak ditemukan."
    )


race_sessions["_date"] = parse_dt(
    race_sessions["date_start"]
)


race = (

    race_sessions
    .sort_values("_date")
    .iloc[-1]

)


SESSION_KEY = int(
    race["session_key"]
)


print("\nRace found")
print("Session Key :", SESSION_KEY)
print("Location    :", race.get("location", "-"))
print("Circuit     :", race.get("circuit_short_name", "-"))


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


top10 = (
    top10
    .sort_values("position")
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
        top10[
            "driver_number"
        ].astype(str)
    )

)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


print("\n" + "=" * 80)
print("TOP 10 FINISHERS")
print("=" * 80)

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

print("\nLoading laps...")


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

    if col in laps.columns:

        laps[col] = pd.to_numeric(
            laps[col],
            errors="coerce"
        )


laps["date_start_dt"] = parse_dt(
    laps["date_start"]
)


laps = laps[

    laps["driver_number"]
    .isin(TOP10)

].copy()


laps = laps.dropna(
    subset=[
        "driver_number",
        "lap_number",
        "lap_duration",
        "date_start_dt"
    ]
)


# ------------------------------------------------
# Lap-end timestamp
# ------------------------------------------------

laps["lap_end_dt"] = (

    laps["date_start_dt"]

    +

    pd.to_timedelta(
        laps["lap_duration"],
        unit="s"
    )

)


print(
    "Top-10 lap records:",
    len(laps)
)


# ================================================================
# 5. LOAD INTERVALS
# ================================================================

print("Loading interval data...")


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


intervals["date_dt"] = parse_dt(
    intervals["date"]
)


intervals = intervals[

    intervals["driver_number"]
    .isin(TOP10)

].copy()


intervals["gap_raw"] = (
    intervals["gap_to_leader"]
)


intervals["gap_seconds"] = pd.to_numeric(
    intervals["gap_to_leader"],
    errors="coerce"
)


# ================================================================
# 6. SAMPLE GAP AT END OF EACH LAP
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


    driver_laps = laps[

        laps["driver_number"]
        ==
        driver_num

    ][
        [
            "lap_number",
            "lap_end_dt"
        ]
    ].copy()


    driver_intervals = intervals[

        intervals["driver_number"]
        ==
        driver_num

    ][
        [
            "date_dt",
            "gap_raw",
            "gap_seconds"
        ]
    ].copy()


    if (
        driver_laps.empty
        or
        driver_intervals.empty
    ):

        continue


    driver_laps = driver_laps.sort_values(
        "lap_end_dt"
    )


    driver_intervals = driver_intervals.sort_values(
        "date_dt"
    )


    # ------------------------------------------------------------
    # Use last interval update BEFORE lap end.
    # This is safer than nearest.
    # ------------------------------------------------------------

    merged = pd.merge_asof(

        driver_laps,

        driver_intervals,

        left_on=
            "lap_end_dt",

        right_on=
            "date_dt",

        direction=
            "backward",

        tolerance=
            pd.Timedelta(
                seconds=10
            )

    )


    # ------------------------------------------------------------
    # Leader sometimes has null gap.
    # If interval timestamp exists + raw gap null:
    # treat as 0 sec.
    # ------------------------------------------------------------

    leader_mask = (

        merged["date_dt"].notna()

        &

        merged["gap_raw"].isna()

    )


    merged.loc[
        leader_mask,
        "gap_seconds"
    ] = 0.0


    merged["driver_number"] = (
        driver_num
    )

    merged["Driver"] = (
        driver
    )

    merged["FinishPosition"] = (
        position
    )


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
# 7. TABLE
# ================================================================

print("\n" + "=" * 80)
print("GAP TO LEADER — END OF LAP")
print("=" * 80)


gap_table = gap_laps[
    [
        "lap_number",
        "FinishPosition",
        "Driver",
        "gap_seconds"
    ]
].copy()


gap_table = gap_table.sort_values(
    [
        "lap_number",
        "FinishPosition"
    ]
)


display(
    gap_table
)


# ================================================================
# 8. PLOT
# ================================================================

fig, ax = plt.subplots(
    figsize=(17, 9)
)


cmap = plt.colormaps[
    "tab10"
]


for i, (_, row) in enumerate(
    top10.iterrows()
):

    driver = row["Driver"]

    position = int(
        row["position"]
    )


    d = gap_laps[

        gap_laps["Driver"]
        ==
        driver

    ].sort_values(
        "lap_number"
    )


    # numeric gaps only
    # +1 LAP etc will naturally be omitted
    d = d[
        d["gap_seconds"].notna()
    ]


    if d.empty:
        continue


    ax.plot(

        d["lap_number"],

        d["gap_seconds"],

        color=cmap(i),

        linewidth=2.2,

        marker="o",

        markersize=2.5,

        label=(
            f"P{position} {driver}"
        )

    )


# ================================================================
# STYLE
# ================================================================

ax.axhline(
    0,
    linewidth=1,
    color="black",
    alpha=0.5
)


ax.set_title(

    "MADRID GP 2026 — TOP 10 GAP EVOLUTION\n"
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


ax.set_xlim(
    left=1
)


ax.set_ylim(
    bottom=0
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


plt.tight_layout()

plt.show()
