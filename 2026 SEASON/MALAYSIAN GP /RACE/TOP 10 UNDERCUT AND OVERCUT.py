# ================================================================
# SEPANG 2026
# TOP 10 UNDERCUT / OVERCUT ANALYSIS
# OPENF1 — GOOGLE COLAB — ONE CELL
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

# Max gap before pit cycle
BATTLE_GAP_MAX = 15.0

# Max difference in pit laps
PIT_WINDOW = 5

# Gap measured this many laps
# after second driver pits
POST_PIT_LAPS = 2


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


mask = (

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
    mask
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


print("=" * 80)
print("UNDERCUT / OVERCUT — SEPANG 2026")
print("=" * 80)

print("Session Key:", SESSION_KEY)


# ================================================================
# 2. DRIVERS
# ================================================================

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
# 3. TOP 10
# ================================================================

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


top10["Driver"] = top10[
    "Driver"
].fillna(
    top10[
        "driver_number"
    ].astype(str)
)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


position_map = (

    top10
    .set_index("driver_number")
    ["position"]
    .to_dict()

)


# ================================================================
# 4. LAPS
# ================================================================

laps = pd.DataFrame(
    api_get(
        "laps",
        {"session_key": SESSION_KEY}
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


laps["date_parsed"] = parse_dt(
    laps["date_start"]
)


laps = laps[
    laps["driver_number"].isin(
        TOP10
    )
].copy()


laps = laps.dropna(
    subset=[
        "driver_number",
        "lap_number",
        "lap_duration",
        "date_parsed"
    ]
)


laps["lap_end"] = (

    laps["date_parsed"]

    +

    pd.to_timedelta(
        laps["lap_duration"],
        unit="s"
    )

)


# ================================================================
# 5. INTERVAL DATA
# ================================================================

intervals = pd.DataFrame(
    api_get(
        "intervals",
        {"session_key": SESSION_KEY}
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
# 6. CONVERT INTERVALS TO LAP-BY-LAP GAP
# ================================================================

frames = []


for driver_num in TOP10:

    dl = laps[

        laps["driver_number"]
        ==
        driver_num

    ][
        [
            "lap_number",
            "lap_end"
        ]
    ].copy()


    di = intervals[

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


    if dl.empty or di.empty:
        continue


    dl = dl.sort_values(
        "lap_end"
    )

    di = di.sort_values(
        "date_parsed"
    )


    merged = pd.merge_asof(

        dl,

        di,

        left_on="lap_end",

        right_on="date_parsed",

        direction="nearest",

        tolerance=pd.Timedelta(
            seconds=10
        )

    )


    # current leader
    leader = (

        merged["date_parsed"].notna()

        &

        merged["gap_raw"].isna()

    )


    merged.loc[
        leader,
        "gap_seconds"
    ] = 0.0


    merged["driver_number"] = (
        driver_num
    )


    frames.append(
        merged
    )


gap_laps = pd.concat(
    frames,
    ignore_index=True
)


# ================================================================
# 7. GAP MATRIX
#
# rows = lap
# columns = driver
# ================================================================

gap_matrix = gap_laps.pivot_table(

    index="lap_number",

    columns="driver_number",

    values="gap_seconds",

    aggfunc="last"

)


# ================================================================
# HELPER: GAP ON LAP
# ================================================================

def get_gap(driver_num, target_lap):

    if driver_num not in gap_matrix.columns:
        return np.nan


    # exact lap first
    if target_lap in gap_matrix.index:

        val = gap_matrix.loc[
            target_lap,
            driver_num
        ]

        if pd.notna(val):
            return float(val)


    # fallback ±1 lap
    candidates = [

        x for x in
        [
            target_lap - 1,
            target_lap + 1
        ]

        if x in gap_matrix.index

    ]


    for lap in candidates:

        val = gap_matrix.loc[
            lap,
            driver_num
        ]

        if pd.notna(val):
            return float(val)


    return np.nan


# ================================================================
# 8. PIT DATA
# ================================================================

pit = pd.DataFrame(
    api_get(
        "pit",
        {"session_key": SESSION_KEY}
    )
)


for col in [
    "driver_number",
    "lap_number",
    "stop_duration",
    "lane_duration"
]:

    if col in pit.columns:

        pit[col] = pd.to_numeric(
            pit[col],
            errors="coerce"
        )


pit = pit[

    pit["driver_number"]
    .isin(TOP10)

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


# stop number for each driver

pit["StopNumber"] = (

    pit
    .groupby(
        "driver_number"
    )
    .cumcount()

    + 1

)


# ================================================================
# 9. FIND POTENTIAL PIT BATTLES
# ================================================================

analysis_rows = []


driver_numbers = (
    sorted(TOP10)
)


for i in range(
    len(driver_numbers)
):

    for j in range(
        i + 1,
        len(driver_numbers)
    ):

        d1 = driver_numbers[i]
        d2 = driver_numbers[j]


        p1 = pit[
            pit["driver_number"] == d1
        ]


        p2 = pit[
            pit["driver_number"] == d2
        ]


        if p1.empty or p2.empty:
            continue


        for _, stop1 in p1.iterrows():

            for _, stop2 in p2.iterrows():

                lap1 = int(
                    stop1["lap_number"]
                )

                lap2 = int(
                    stop2["lap_number"]
                )


                # same lap = no clear under/overcut
                if lap1 == lap2:
                    continue


                if abs(lap1 - lap2) > PIT_WINDOW:
                    continue


                # -----------------------------------------------
                # Determine early vs late pitter
                # -----------------------------------------------

                if lap1 < lap2:

                    early = d1
                    late = d2

                    early_pit = lap1
                    late_pit = lap2

                    early_stop_num = int(
                        stop1["StopNumber"]
                    )

                    late_stop_num = int(
                        stop2["StopNumber"]
                    )


                else:

                    early = d2
                    late = d1

                    early_pit = lap2
                    late_pit = lap1

                    early_stop_num = int(
                        stop2["StopNumber"]
                    )

                    late_stop_num = int(
                        stop1["StopNumber"]
                    )


                # -----------------------------------------------
                # measurement points
                # -----------------------------------------------

                pre_lap = (
                    early_pit - 1
                )

                post_lap = (
                    late_pit
                    +
                    POST_PIT_LAPS
                )


                early_pre = get_gap(
                    early,
                    pre_lap
                )

                late_pre = get_gap(
                    late,
                    pre_lap
                )


                early_post = get_gap(
                    early,
                    post_lap
                )

                late_post = get_gap(
                    late,
                    post_lap
                )


                if any(
                    pd.isna(x)

                    for x in [
                        early_pre,
                        late_pre,
                        early_post,
                        late_post
                    ]
                ):
                    continue


                # -----------------------------------------------
                # relative gap
                #
                # positive = early pitter is behind
                # negative = early pitter is ahead
                # -----------------------------------------------

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


                # cars need to be reasonably close beforehand

                if abs(pre_relative) > BATTLE_GAP_MAX:
                    continue


                swing = (

                    post_relative

                    -

                    pre_relative

                )


                # -----------------------------------------------
                # CLASSIFICATION
                # -----------------------------------------------

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


                elif swing < -0.25:

                    classification = (
                        "UNDERCUT GAIN"
                    )


                elif swing > 0.25:

                    classification = (
                        "OVERCUT GAIN"
                    )


                else:

                    classification = (
                        "NEUTRAL"
                    )


                analysis_rows.append({

                    "EarlyDriver":
                        driver_map.get(
                            early,
                            str(early)
                        ),

                    "LateDriver":
                        driver_map.get(
                            late,
                            str(late)
                        ),

                    "EarlyFinish":
                        int(
                            position_map[
                                early
                            ]
                        ),

                    "LateFinish":
                        int(
                            position_map[
                                late
                            ]
                        ),

                    "EarlyStop":
                        early_stop_num,

                    "LateStop":
                        late_stop_num,

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

                    "Result":
                        classification

                })


# ================================================================
# 10. RESULT DATAFRAME
# ================================================================

analysis = pd.DataFrame(
    analysis_rows
)


if analysis.empty:

    raise RuntimeError(
        "Tidak ditemukan pit-cycle battles "
        "dengan kriteria yang dipilih."
    )


# eliminate exact duplicate analyses
analysis = analysis.drop_duplicates(

    subset=[
        "EarlyDriver",
        "LateDriver",
        "EarlyPitLap",
        "LatePitLap"
    ]

)


# magnitude

analysis["GainMagnitude"] = (
    analysis["Swing"].abs()
)


analysis = analysis.sort_values(
    "GainMagnitude",
    ascending=False
).reset_index(
    drop=True
)


# ================================================================
# 11. PRETTY TABLE
# ================================================================

table = analysis.copy()


table["Before"] = table[
    "PreRelativeGap"
].map(
    lambda x:
    f"{x:+.3f}s"
)


table["After"] = table[
    "PostRelativeGap"
].map(
    lambda x:
    f"{x:+.3f}s"
)


table["Net Swing"] = table[
    "Swing"
].map(
    lambda x:
    f"{x:+.3f}s"
)


print("\n" + "=" * 100)
print("UNDERCUT / OVERCUT ANALYSIS")
print("=" * 100)

print(
    "Negative swing = earlier pitter gained"
)

print(
    "Positive swing = later pitter gained"
)


display(

    table[
        [
            "EarlyDriver",
            "LateDriver",
            "EarlyPitLap",
            "LatePitLap",
            "Before",
            "After",
            "Net Swing",
            "Result"
        ]
    ]

)


# ================================================================
# 12. GRAPH
# ================================================================

plot_df = analysis.copy()


plot_df["Battle"] = (

    plot_df["EarlyDriver"]

    +

    " L"

    +

    plot_df["EarlyPitLap"]
    .astype(str)

    +

    "  vs  "

    +

    plot_df["LateDriver"]

    +

    " L"

    +

    plot_df["LatePitLap"]
    .astype(str)

)


# limit graph to strongest 15
plot_df = (
    plot_df
    .head(15)
    .iloc[::-1]
)


fig, ax = plt.subplots(
    figsize=(14, 9)
)


bars = ax.barh(

    plot_df["Battle"],

    plot_df["Swing"]

)


# zero = neutral
ax.axvline(
    0,
    linewidth=1.5
)


# labels

for bar, (_, row) in zip(
    bars,
    plot_df.iterrows()
):

    x = row["Swing"]


    ax.text(

        x,

        bar.get_y()
        +
        bar.get_height() / 2,

        (
            f" {x:+.2f}s "
            f"{row['Result']}"
        ),

        va="center",

        ha=(
            "left"
            if x >= 0
            else "right"
        ),

        fontsize=8

    )


ax.set_title(

    "SEPANG 2026 — UNDERCUT / OVERCUT ANALYSIS\n"
    "← Earlier Pitter Gain | Later Pitter Gain →",

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
