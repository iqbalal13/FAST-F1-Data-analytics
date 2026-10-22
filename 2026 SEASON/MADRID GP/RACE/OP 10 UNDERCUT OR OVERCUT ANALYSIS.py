# ================================================================
# MADRID GP 2026 — MADRING
# TOP 10 UNDERCUT / OVERCUT ANALYSIS
#
# OPENF1
# GOOGLE COLAB — ONE CELL
#
# LOGIC
# ------------------------------------------------
# Relative gap:
#
#   gap early pitter to leader
#   -
#   gap late pitter to leader
#
# Positive relative gap:
# early pitter is BEHIND late pitter
#
# Negative relative gap:
# early pitter is AHEAD
#
# Swing:
#
#   post-relative-gap
#   -
#   pre-relative-gap
#
# Negative swing = UNDERCUT gain
# Positive swing = OVERCUT gain
#
# Successful undercut:
# behind before cycle -> ahead after cycle
#
# Successful overcut:
# early pitter ahead before -> late pitter ahead after
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

# maximum pre-cycle gap for relevant battle
BATTLE_GAP_MAX = 30.0

# max number of laps between pit stops
PIT_WINDOW = 3

# evaluate 1 lap after later pitter pits
POST_PIT_LAPS = 1

# less than 0.20s = neutral
NEUTRAL_THRESHOLD = 0.20


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
# API GET
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

        elapsed = (
            time.time()
            -
            LAST_REQUEST_TIME
        )


        if elapsed < MIN_REQUEST_INTERVAL:

            time.sleep(
                MIN_REQUEST_INTERVAL
                -
                elapsed
            )


        try:

            r = http.get(
                url,
                params=params,
                timeout=90
            )

            LAST_REQUEST_TIME = (
                time.time()
            )


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


        if r.status_code == 429:

            retry_after = (
                r.headers.get(
                    "Retry-After"
                )
            )


            if retry_after:

                try:
                    wait = float(
                        retry_after
                    )

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

            print(
                "URL    :",
                r.url
            )

            print(
                "Status :",
                r.status_code
            )

            print(
                "Body   :",
                r.text[:500]
            )

            raise RuntimeError(
                f"OpenF1 HTTP "
                f"{r.status_code}"
            )


        data = r.json()


        if (
            not data
            and
            not allow_empty
        ):

            raise RuntimeError(
                f"No data returned "
                f"from {endpoint}"
            )


        return data


    raise RuntimeError(
        f"OpenF1 failed after "
        f"{max_retries} retries: "
        f"{endpoint}"
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
# 1. FIND MADRID RACE
# ================================================================

print("=" * 90)

print(
    "MADRID GP 2026 — "
    "UNDERCUT / OVERCUT ANALYSIS"
)

print("=" * 90)


sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)


location_col = (

    sessions["location"]

    if
    "location"
    in
    sessions.columns

    else

    pd.Series(
        "",
        index=sessions.index
    )

)


circuit_col = (

    sessions[
        "circuit_short_name"
    ]

    if
    "circuit_short_name"
    in
    sessions.columns

    else

    pd.Series(
        "",
        index=sessions.index
    )

)


meeting_col = (

    sessions[
        "meeting_name"
    ]

    if
    "meeting_name"
    in
    sessions.columns

    else

    pd.Series(
        "",
        index=sessions.index
    )

)


madrid_mask = (

    location_col
    .astype(str)
    .str.contains(
        "Madrid|Madring",
        case=False,
        regex=True,
        na=False
    )

    |

    circuit_col
    .astype(str)
    .str.contains(
        "Madrid|Madring",
        case=False,
        regex=True,
        na=False
    )

    |

    meeting_col
    .astype(str)
    .str.contains(
        "Madrid",
        case=False,
        na=False
    )

)


madrid = sessions[
    madrid_mask
].copy()


race_sessions = madrid[

    madrid[
        "session_name"
    ]

    .astype(str)

    .str.lower()

    .eq(
        "race"
    )

].copy()


if race_sessions.empty:

    raise RuntimeError(
        "Madrid / Madring 2026 "
        "race tidak ditemukan."
    )


race_sessions["_date"] = parse_dt(
    race_sessions["date_start"]
)


race = (

    race_sessions

    .sort_values(
        "_date"
    )

    .iloc[-1]

)


SESSION_KEY = int(
    race[
        "session_key"
    ]
)


print(
    "Session Key:",
    SESSION_KEY
)

print(
    "Location   :",
    race.get(
        "location",
        "-"
    )
)

print(
    "Circuit    :",
    race.get(
        "circuit_short_name",
        "-"
    )
)


# ================================================================
# 2. DRIVERS
# ================================================================

print(
    "\nLoading drivers..."
)


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
    subset=[
        "driver_number"
    ]
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

    .set_index(
        "driver_number"
    )

    ["name_acronym"]

    .to_dict()

)


# ================================================================
# 3. TOP 10 RESULT
# ================================================================

print(
    "Loading race result..."
)


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
    .between(
        1,
        10
    )

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
    .map(
        driver_map
    )

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
    top10[
        "driver_number"
    ]
    .tolist()
)


finish_map = (

    top10

    .set_index(
        "driver_number"
    )

    ["position"]

    .to_dict()

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
# 4. LAPS
# ================================================================

print(
    "\nLoading laps..."
)


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
    .isin(
        TOP10
    )

].copy()


laps = laps.dropna(
    subset=[
        "driver_number",
        "lap_number",
        "lap_duration",
        "date_start_dt"
    ]
)


laps["lap_end_dt"] = (

    laps["date_start_dt"]

    +

    pd.to_timedelta(
        laps["lap_duration"],
        unit="s"
    )

)


# ================================================================
# 5. PIT DATA
# ================================================================

print(
    "Loading pit stops..."
)


pit = pd.DataFrame(
    api_get(
        "pit",
        {
            "session_key":
                SESSION_KEY
        }
    )
)


for col in [
    "driver_number",
    "lap_number",
    "lane_duration",
    "stop_duration"
]:

    if col in pit.columns:

        pit[col] = pd.to_numeric(
            pit[col],
            errors="coerce"
        )


pit = pit[

    pit["driver_number"]
    .isin(
        TOP10
    )

].copy()


pit = pit.dropna(
    subset=[
        "driver_number",
        "lap_number"
    ]
)


pit["driver_number"] = (

    pit["driver_number"]
    .astype(int)

)


pit["lap_number"] = (

    pit["lap_number"]
    .astype(int)

)


pit = pit.sort_values(
    [
        "driver_number",
        "lap_number"
    ]
)


# ================================================================
# IMPORTANT:
# stop number per driver
#
# stop 1 only compared with stop 1
# stop 2 only compared with stop 2
# ================================================================

pit["StopNumber"] = (

    pit

    .groupby(
        "driver_number"
    )

    .cumcount()

    +
    1

)


pit["Driver"] = (

    pit["driver_number"]
    .map(
        driver_map
    )

)


print("\n" + "=" * 90)
print("TOP-10 PIT STOPS")
print("=" * 90)


pit_cols = [
    "Driver",
    "StopNumber",
    "lap_number"
]


if "lane_duration" in pit.columns:

    pit_cols.append(
        "lane_duration"
    )


display(

    pit[
        pit_cols
    ]

    .rename(
        columns={
            "lap_number":
                "Pit Lap",

            "lane_duration":
                "Pit Lane Time"
        }
    )

)


# ================================================================
# 6. INTERVALS
# ================================================================

print(
    "\nLoading interval data..."
)


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


intervals["gap_raw"] = (

    intervals[
        "gap_to_leader"
    ]

)


intervals["gap_seconds"] = pd.to_numeric(
    intervals[
        "gap_to_leader"
    ],
    errors="coerce"
)


intervals = intervals[

    intervals["driver_number"]
    .isin(
        TOP10
    )

].copy()


# ================================================================
# 7. LAP-BY-LAP GAP MATRIX
# ================================================================

gap_frames = []


for driver_num in TOP10:

    dl = laps[

        laps["driver_number"]
        ==
        driver_num

    ][
        [
            "lap_number",
            "lap_end_dt"
        ]
    ].copy()


    di = intervals[

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


    if dl.empty or di.empty:

        continue


    dl = dl.sort_values(
        "lap_end_dt"
    )


    di = di.sort_values(
        "date_dt"
    )


    merged = pd.merge_asof(

        dl,

        di,

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


    # Leader
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


    gap_frames.append(
        merged
    )


if not gap_frames:

    raise RuntimeError(
        "Tidak bisa membuat lap-gap data."
    )


lap_gaps = pd.concat(
    gap_frames,
    ignore_index=True
)


gap_matrix = (

    lap_gaps

    .pivot_table(

        index=
            "lap_number",

        columns=
            "driver_number",

        values=
            "gap_seconds",

        aggfunc=
            "last"

    )

)


# ================================================================
# GET GAP HELPER
# ================================================================

def get_gap(
    driver_number,
    target_lap
):

    if (
        driver_number
        not in
        gap_matrix.columns
    ):

        return np.nan


    # exact lap
    if target_lap in gap_matrix.index:

        value = gap_matrix.loc[
            target_lap,
            driver_number
        ]

        if pd.notna(value):

            return float(
                value
            )


    # neighbouring lap fallback
    for offset in [
        -1,
        1
    ]:

        lap = (
            target_lap
            +
            offset
        )


        if lap in gap_matrix.index:

            value = gap_matrix.loc[
                lap,
                driver_number
            ]

            if pd.notna(value):

                return float(
                    value
                )


    return np.nan


# ================================================================
# 8. FIND PIT-CYCLE BATTLES
# ================================================================

analysis_rows = []


driver_numbers = sorted(
    TOP10
)


for i in range(
    len(driver_numbers)
):

    for j in range(
        i + 1,
        len(driver_numbers)
    ):

        driver_a = (
            driver_numbers[i]
        )

        driver_b = (
            driver_numbers[j]
        )


        pits_a = pit[

            pit["driver_number"]
            ==
            driver_a

        ]


        pits_b = pit[

            pit["driver_number"]
            ==
            driver_b

        ]


        if (
            pits_a.empty
            or
            pits_b.empty
        ):

            continue


        # ========================================================
        # ONLY COMPARE SAME STOP NUMBER
        # ========================================================

        common_stops = sorted(

            set(
                pits_a["StopNumber"]
            )

            &

            set(
                pits_b["StopNumber"]
            )

        )


        for stop_number in common_stops:

            pa = pits_a[

                pits_a["StopNumber"]
                ==
                stop_number

            ].iloc[0]


            pb = pits_b[

                pits_b["StopNumber"]
                ==
                stop_number

            ].iloc[0]


            lap_a = int(
                pa["lap_number"]
            )


            lap_b = int(
                pb["lap_number"]
            )


            # same lap:
            # no clean early/late strategy split
            if lap_a == lap_b:

                continue


            # too far apart
            if (
                abs(
                    lap_a
                    -
                    lap_b
                )
                >
                PIT_WINDOW
            ):

                continue


            # ====================================================
            # EARLY / LATE PITTER
            # ====================================================

            if lap_a < lap_b:

                early_driver = (
                    driver_a
                )

                late_driver = (
                    driver_b
                )

                early_pit = (
                    lap_a
                )

                late_pit = (
                    lap_b
                )

                early_stop = (
                    pa
                )

                late_stop = (
                    pb
                )


            else:

                early_driver = (
                    driver_b
                )

                late_driver = (
                    driver_a
                )

                early_pit = (
                    lap_b
                )

                late_pit = (
                    lap_a
                )

                early_stop = (
                    pb
                )

                late_stop = (
                    pa
                )


            # ====================================================
            # MEASUREMENT POINTS
            # ====================================================

            pre_lap = (
                early_pit
                -
                1
            )


            post_lap = (

                late_pit

                +

                POST_PIT_LAPS

            )


            early_pre = get_gap(
                early_driver,
                pre_lap
            )


            late_pre = get_gap(
                late_driver,
                pre_lap
            )


            early_post = get_gap(
                early_driver,
                post_lap
            )


            late_post = get_gap(
                late_driver,
                post_lap
            )


            values = [
                early_pre,
                late_pre,
                early_post,
                late_post
            ]


            if any(
                pd.isna(x)
                for x in values
            ):

                continue


            # ====================================================
            # RELATIVE GAP
            #
            # + = early pitter behind
            # - = early pitter ahead
            # ====================================================

            pre_relative = (

                early_pre
                -
                late_pre

            )


            post_relative = (

                early_post
                -
                late_post

            )


            # relevant battle only
            if (
                abs(
                    pre_relative
                )
                >
                BATTLE_GAP_MAX
            ):

                continue


            # ====================================================
            # SWING
            #
            # negative = undercut direction
            # positive = overcut direction
            # ====================================================

            swing = (

                post_relative
                -
                pre_relative

            )


            # ====================================================
            # CLASSIFICATION
            # ====================================================

            if (

                pre_relative > 0

                and

                post_relative < 0

            ):

                classification = (
                    "SUCCESSFUL UNDERCUT"
                )


            elif (

                pre_relative < 0

                and

                post_relative > 0

            ):

                classification = (
                    "SUCCESSFUL OVERCUT"
                )


            elif (
                swing
                <
                -NEUTRAL_THRESHOLD
            ):

                classification = (
                    "UNDERCUT GAIN"
                )


            elif (
                swing
                >
                NEUTRAL_THRESHOLD
            ):

                classification = (
                    "OVERCUT GAIN"
                )


            else:

                classification = (
                    "NEUTRAL"
                )


            # ====================================================
            # PIT-LANE DIFFERENCE
            # ====================================================

            early_lane = (
                early_stop.get(
                    "lane_duration",
                    np.nan
                )
            )


            late_lane = (
                late_stop.get(
                    "lane_duration",
                    np.nan
                )
            )


            pit_lane_delta = np.nan


            if (
                pd.notna(early_lane)
                and
                pd.notna(late_lane)
            ):

                pit_lane_delta = (

                    float(early_lane)

                    -

                    float(late_lane)

                )


            # ====================================================
            # SAVE
            # ====================================================

            analysis_rows.append({

                "Stop":
                    int(stop_number),

                "EarlyDriver":
                    driver_map.get(
                        early_driver,
                        str(early_driver)
                    ),

                "LateDriver":
                    driver_map.get(
                        late_driver,
                        str(late_driver)
                    ),

                "EarlyFinish":
                    int(
                        finish_map[
                            early_driver
                        ]
                    ),

                "LateFinish":
                    int(
                        finish_map[
                            late_driver
                        ]
                    ),

                "EarlyPitLap":
                    early_pit,

                "LatePitLap":
                    late_pit,

                "PreLap":
                    pre_lap,

                "PostLap":
                    post_lap,

                "PreRelativeGap":
                    pre_relative,

                "PostRelativeGap":
                    post_relative,

                "Swing":
                    swing,

                "PitLaneDelta":
                    pit_lane_delta,

                "Result":
                    classification

            })


# ================================================================
# 9. RESULTS
# ================================================================

analysis = pd.DataFrame(
    analysis_rows
)


if analysis.empty:

    raise RuntimeError(

        "Tidak ada valid undercut/overcut battles.\n"
        "Coba naikkan PIT_WINDOW atau BATTLE_GAP_MAX."

    )


analysis = analysis.drop_duplicates(

    subset=[
        "Stop",
        "EarlyDriver",
        "LateDriver"
    ]

)


analysis["GainMagnitude"] = (

    analysis["Swing"]
    .abs()

)


analysis = (

    analysis

    .sort_values(
        "GainMagnitude",
        ascending=False
    )

    .reset_index(
        drop=True
    )

)


# ================================================================
# TABLE
# ================================================================

table = analysis.copy()


table["Before"] = (

    table["PreRelativeGap"]

    .map(
        lambda x:
        f"{x:+.3f}s"
    )

)


table["After"] = (

    table["PostRelativeGap"]

    .map(
        lambda x:
        f"{x:+.3f}s"
    )

)


table["Net Swing"] = (

    table["Swing"]

    .map(
        lambda x:
        f"{x:+.3f}s"
    )

)


table["Pit Lane Δ"] = (

    table["PitLaneDelta"]

    .map(
        lambda x:
        f"{x:+.3f}s"
        if pd.notna(x)
        else "-"
    )

)


print("\n" + "=" * 110)

print(
    "MADRID GP 2026 — UNDERCUT / OVERCUT RESULTS"
)

print("=" * 110)

print(
    "Negative swing = earlier pitter gained → undercut"
)

print(
    "Positive swing = later pitter gained → overcut"
)


display(

    table[
        [
            "Stop",
            "EarlyDriver",
            "LateDriver",
            "EarlyPitLap",
            "LatePitLap",
            "Before",
            "After",
            "Net Swing",
            "Pit Lane Δ",
            "Result"
        ]
    ]

)


# ================================================================
# 10. GRAPH
# ================================================================

plot_df = analysis[

    analysis["Swing"].abs()
    >=
    NEUTRAL_THRESHOLD

].copy()


if plot_df.empty:

    plot_df = (
        analysis.copy()
    )


plot_df = (

    plot_df

    .head(20)

    .copy()

)


plot_df["Battle"] = (

    "S"

    +

    plot_df["Stop"]
    .astype(str)

    +

    " | "

    +

    plot_df["EarlyDriver"]

    +

    " L"

    +

    plot_df["EarlyPitLap"]
    .astype(str)

    +

    " vs "

    +

    plot_df["LateDriver"]

    +

    " L"

    +

    plot_df["LatePitLap"]
    .astype(str)

)


plot_df = (

    plot_df
    .iloc[::-1]

)


colors = [

    "tab:blue"
    if x < 0

    else
    "tab:orange"

    for x in plot_df["Swing"]

]


# ================================================================
# DYNAMIC HEIGHT
# ================================================================

n = len(
    plot_df
)


fig_height = max(
    4.5,
    n * 0.65 + 2
)


fig, ax = plt.subplots(

    figsize=(
        15,
        fig_height
    )

)


bars = ax.barh(

    plot_df["Battle"],

    plot_df["Swing"],

    color=colors,

    height=0.55

)


ax.axvline(
    0,
    color="black",
    linewidth=1.2
)


max_abs = max(

    plot_df[
        "Swing"
    ].abs().max(),

    1

)


offset = (
    max_abs * 0.025
)


# ================================================================
# LABELS
# ================================================================

for bar, (_, row) in zip(

    bars,

    plot_df.iterrows()

):

    value = (
        row["Swing"]
    )


    ax.text(

        value
        +
        (
            offset
            if value >= 0
            else
            -offset
        ),

        bar.get_y()
        +
        bar.get_height() / 2,

        f"{value:+.2f}s",

        va="center",

        ha=(
            "left"
            if value >= 0
            else
            "right"
        ),

        fontsize=9,

        fontweight="bold"

    )


    ax.text(

        value / 2,

        bar.get_y()
        +
        bar.get_height() / 2,

        row["Result"],

        va="center",

        ha="center",

        fontsize=7.5,

        color="white",

        fontweight="bold"

    )


# ================================================================
# LIMITS
# ================================================================

xmin = min(
    plot_df["Swing"].min(),
    0
)


xmax = max(
    plot_df["Swing"].max(),
    0
)


margin = max(
    abs(xmin),
    abs(xmax),
    1
) * 0.18


ax.set_xlim(
    xmin - margin,
    xmax + margin
)


# ================================================================
# STYLE
# ================================================================

ax.set_title(

    "MADRID GP 2026 — UNDERCUT / OVERCUT PIT-CYCLE SWING\n"
    "← UNDERCUT GAIN | OVERCUT GAIN →",

    fontsize=16,

    fontweight="bold",

    pad=18

)


ax.set_xlabel(
    "Relative Gap Swing (seconds)"
)


ax.set_ylabel(
    "Pit Battle"
)


ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


plt.tight_layout()

plt.show()


# ================================================================
# 11. SUCCESSFUL POSITION REVERSALS
# ================================================================

successful = analysis[

    analysis["Result"]
    .isin(
        [
            "SUCCESSFUL UNDERCUT",
            "SUCCESSFUL OVERCUT"
        ]
    )

].copy()


print("\n" + "=" * 110)
print("SUCCESSFUL POSITION REVERSALS")
print("=" * 110)


if successful.empty:

    print(
        "Tidak ada clean position reversal "
        "dalam pit cycle yang memenuhi filter."
    )


else:

    display(

        successful[
            [
                "Stop",
                "EarlyDriver",
                "LateDriver",
                "EarlyPitLap",
                "LatePitLap",
                "PreRelativeGap",
                "PostRelativeGap",
                "Swing",
                "Result"
            ]
        ]

    )


# ================================================================
# 12. STRONGEST UNDERCUTS
# ================================================================

undercuts = analysis[

    analysis["Swing"]
    <
    -NEUTRAL_THRESHOLD

].sort_values(
    "Swing"
)


print("\n" + "=" * 110)
print("STRONGEST UNDERCUT GAINS")
print("=" * 110)


if undercuts.empty:

    print(
        "Tidak ada significant undercut gain."
    )

else:

    display(

        undercuts[
            [
                "Stop",
                "EarlyDriver",
                "LateDriver",
                "EarlyPitLap",
                "LatePitLap",
                "Swing",
                "PitLaneDelta",
                "Result"
            ]
        ]
        .head(10)

    )


# ================================================================
# 13. STRONGEST OVERCUTS
# ================================================================

overcuts = analysis[

    analysis["Swing"]
    >
    NEUTRAL_THRESHOLD

].sort_values(
    "Swing",
    ascending=False
)


print("\n" + "=" * 110)
print("STRONGEST OVERCUT GAINS")
print("=" * 110)


if overcuts.empty:

    print(
        "Tidak ada significant overcut gain."
    )

else:

    display(

        overcuts[
            [
                "Stop",
                "EarlyDriver",
                "LateDriver",
                "EarlyPitLap",
                "LatePitLap",
                "Swing",
                "PitLaneDelta",
                "Result"
            ]
        ]
        .head(10)

    )
