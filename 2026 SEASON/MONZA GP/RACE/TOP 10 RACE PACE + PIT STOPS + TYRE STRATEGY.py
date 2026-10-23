# ================================================================
# ITALIAN GP 2026 — MONZA
# TOP 10 RACE PACE + PIT STOPS + TYRE STRATEGY
# OPENF1 — GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time
import random
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from matplotlib.lines import Line2D

YEAR = 2026
BASE = "https://api.openf1.org/v1"

LAST_REQUEST_TIME = time.time()
MIN_REQUEST_INTERVAL = 1.10

http = requests.Session()

http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})


def api_get(endpoint, params=None, allow_empty=False, max_retries=10):

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

            time.sleep(wait)

            continue


        if r.status_code == 429:

            wait = min(
                4 + attempt * 4,
                40
            )

            wait += random.uniform(
                0.3,
                1.0
            )

            print(
                f"⚠️ 429 {endpoint}; "
                f"retry in {wait:.1f}s"
            )

            time.sleep(wait)

            continue


        if r.status_code != 200:

            print(
                r.url,
                r.status_code,
                r.text[:500]
            )

            raise RuntimeError(
                f"OpenF1 HTTP "
                f"{r.status_code}"
            )


        data = r.json()

        if not data and not allow_empty:

            raise RuntimeError(
                f"No data from {endpoint}"
            )

        return data


    raise RuntimeError(
        f"OpenF1 failed: {endpoint}"
    )


def parse_dt(x):

    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


def format_seconds(seconds):

    if pd.isna(seconds):
        return "-"

    m = int(
        float(seconds) // 60
    )

    s = float(seconds) % 60

    return f"{m}:{s:06.3f}"


def find_monza_race():

    sessions = pd.DataFrame(
        api_get(
            "sessions",
            {"year": YEAR}
        )
    )


    location = sessions.get(
        "location",
        pd.Series(
            "",
            index=sessions.index
        )
    )


    circuit = sessions.get(
        "circuit_short_name",
        pd.Series(
            "",
            index=sessions.index
        )
    )


    mask = (

        location.astype(str)
        .str.contains(
            "Monza",
            case=False,
            na=False
        )

        |

        circuit.astype(str)
        .str.contains(
            "Monza",
            case=False,
            na=False
        )

    )


    race = sessions[

        mask

        &

        sessions["session_name"]
        .astype(str)
        .str.lower()
        .eq("race")

    ].copy()


    if race.empty:

        raise RuntimeError(
            "Monza race tidak ditemukan."
        )


    race["_date"] = parse_dt(
        race["date_start"]
    )


    return (
        race
        .sort_values("_date")
        .iloc[-1]
    )


session = find_monza_race()

SESSION_KEY = int(
    session["session_key"]
)


print("=" * 80)
print("ITALIAN GP 2026 — MONZA — RACE PACE + STRATEGY")
print("=" * 80)

print(
    "Session Key:",
    SESSION_KEY
)


# ================================================================
# DRIVERS + TOP 10
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
    .reset_index(drop=True)
)


top10["driver_number"] = (
    top10["driver_number"]
    .astype(int)
)


top10["Driver"] = (
    top10["driver_number"]
    .map(driver_map)
)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


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
# LAPS
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

    if col in laps.columns:

        laps[col] = pd.to_numeric(
            laps[col],
            errors="coerce"
        )


laps = laps[

    laps["driver_number"]
    .isin(TOP10)

].copy()


laps = laps.dropna(
    subset=[
        "driver_number",
        "lap_number",
        "lap_duration"
    ]
)


# ================================================================
# PIT STOPS
# ================================================================

pit = pd.DataFrame(
    api_get(
        "pit",
        {
            "session_key":
                SESSION_KEY
        },
        allow_empty=True
    )
)


if not pit.empty:

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
        .isin(TOP10)

    ].copy()


    pit["StopTime"] = (

        pit["stop_duration"]

        if "stop_duration" in pit.columns

        else np.nan
    )


else:

    pit = pd.DataFrame(
        columns=[
            "driver_number",
            "lap_number",
            "lane_duration",
            "stop_duration",
            "StopTime"
        ]
    )


# ================================================================
# STINTS
# ================================================================

stints = pd.DataFrame(
    api_get(
        "stints",
        {
            "session_key":
                SESSION_KEY
        },
        allow_empty=True
    )
)


if not stints.empty:

    for col in [
        "driver_number",
        "stint_number",
        "lap_start",
        "lap_end",
        "tyre_age_at_start"
    ]:

        if col in stints.columns:

            stints[col] = pd.to_numeric(
                stints[col],
                errors="coerce"
            )


    stints = stints[

        stints["driver_number"]
        .isin(TOP10)

    ].copy()


# ================================================================
# CLEAN RACE PACE
# ================================================================

pace_frames = []


for _, result_row in top10.iterrows():

    driver_num = int(
        result_row["driver_number"]
    )


    d = laps[

        laps["driver_number"]
        .eq(driver_num)

    ].copy()


    d = d[

        (d["lap_number"] > 1)

        &

        (d["lap_duration"] > 0)

    ].copy()


    if "is_pit_out_lap" in d.columns:

        d = d[
            d["is_pit_out_lap"]
            != True
        ].copy()


    if not pit.empty:

        pit_laps = (

            pit[
                pit["driver_number"]
                .eq(driver_num)
            ]

            ["lap_number"]

            .dropna()

            .astype(int)

            .tolist()
        )


        if pit_laps:

            d = d[

                ~d["lap_number"]
                .astype(int)
                .isin(
                    pit_laps
                )

            ].copy()


    if d.empty:
        continue


    median_time = (
        d["lap_duration"]
        .median()
    )


    d = d[

        d["lap_duration"]

        <=

        median_time
        +
        8.0

    ].copy()


    if d.empty:
        continue


    d = d.sort_values(
        "lap_number"
    )


    d["RacePace"] = (

        d["lap_duration"]

        .rolling(
            window=3,
            center=True,
            min_periods=1
        )

        .median()
    )


    d["Driver"] = (
        result_row["Driver"]
    )


    d["Position"] = int(
        result_row["position"]
    )


    pace_frames.append(
        d
    )


if not pace_frames:

    raise RuntimeError(
        "Tidak ada valid race pace."
    )


pace = pd.concat(
    pace_frames,
    ignore_index=True
)


# ================================================================
# SUMMARY
# ================================================================

pace_summary = (

    pace

    .groupby(
        [
            "Position",
            "Driver",
            "driver_number"
        ]
    )

    .agg(

        MedianPace=(
            "RacePace",
            "median"
        ),

        MeanPace=(
            "RacePace",
            "mean"
        ),

        ValidLaps=(
            "lap_number",
            "count"
        )
    )

    .reset_index()

    .sort_values(
        "Position"
    )
)


if not pit.empty:

    pit_count = (
        pit.groupby(
            "driver_number"
        )
        .size()
    )


    pace_summary["PitStops"] = (

        pace_summary["driver_number"]

        .map(
            pit_count
        )

        .fillna(0)

        .astype(int)
    )


else:

    pace_summary["PitStops"] = 0


summary_display = (
    pace_summary.copy()
)


summary_display["Median Pace"] = (

    summary_display["MedianPace"]
    .apply(
        format_seconds
    )
)


summary_display["Mean Pace"] = (

    summary_display["MeanPace"]
    .apply(
        format_seconds
    )
)


print()
print("=" * 80)
print("RACE PACE SUMMARY")
print("=" * 80)


display(

    summary_display[
        [
            "Position",
            "Driver",
            "Median Pace",
            "Mean Pace",
            "ValidLaps",
            "PitStops"
        ]
    ]
)


# ================================================================
# GRAPH — 2 PANELS
# ================================================================

fig, (
    ax1,
    ax2
) = plt.subplots(

    2,
    1,

    figsize=(16, 12),

    gridspec_kw={
        "height_ratios":
            [2.3, 1.2]
    },

    sharex=True
)


cmap = plt.colormaps[
    "tab10"
]


driver_colors = {

    int(row["driver_number"]):
        cmap(i)

    for i, (_, row)
    in enumerate(
        top10.iterrows()
    )
}


# ================================================================
# TOP — RACE PACE
# ================================================================

for _, result_row in top10.iterrows():

    driver_num = int(
        result_row["driver_number"]
    )

    driver = (
        result_row["Driver"]
    )

    position = int(
        result_row["position"]
    )


    d = pace[

        pace["driver_number"]
        .eq(driver_num)

    ].copy()


    if d.empty:
        continue


    color = (
        driver_colors[
            driver_num
        ]
    )


    ax1.plot(

        d["lap_number"],

        d["RacePace"],

        linewidth=2,

        color=color,

        label=(
            f"P{position} {driver}"
        )
    )


    if not pit.empty:

        dp = pit[

            pit["driver_number"]
            .eq(driver_num)

        ]


        for _, stop in dp.iterrows():

            if pd.isna(
                stop["lap_number"]
            ):
                continue


            pit_lap = int(
                stop["lap_number"]
            )


            nearest_idx = (

                d["lap_number"]

                .sub(
                    pit_lap
                )

                .abs()

                .idxmin()
            )


            pit_y = d.loc[
                nearest_idx,
                "RacePace"
            ]


            ax1.scatter(

                pit_lap,
                pit_y,

                marker="v",

                s=80,

                color=color,

                edgecolor="black",

                linewidth=0.7,

                zorder=10
            )


ax1.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 RACE PACE + PIT STOPS\n"
    "3-Lap Rolling Median | Lower = Faster",

    fontsize=16,

    fontweight="bold",

    pad=16
)


ax1.set_ylabel(
    "Race Pace (seconds)"
)


ax1.grid(
    alpha=0.25,
    linestyle="--"
)


ax1.legend(
    ncol=5,
    fontsize=9,
    loc="upper center"
)


# ================================================================
# BOTTOM — TYRE STINT STRATEGY
# ================================================================

compound_colors = {
    "SOFT": "red",
    "MEDIUM": "gold",
    "HARD": "lightgray",
    "INTERMEDIATE": "green",
    "WET": "blue",
    "UNKNOWN": "black"
}


MAX_LAP = int(
    laps["lap_number"]
    .max()
)


yticks = []
ylabels = []


for y_idx, (_, result_row) in enumerate(
    top10.iterrows()
):

    driver_num = int(
        result_row["driver_number"]
    )

    driver = (
        result_row["Driver"]
    )

    position = int(
        result_row["position"]
    )


    yticks.append(
        y_idx
    )


    ylabels.append(
        f"P{position} {driver}"
    )


    has_stint = False


    if not stints.empty:

        ds = stints[

            stints["driver_number"]
            .eq(driver_num)

        ].copy()


        if "stint_number" in ds.columns:

            ds = ds.sort_values(
                "stint_number"
            )

        else:

            ds = ds.sort_values(
                "lap_start"
            )


        for _, stint in ds.iterrows():

            if (
                pd.isna(
                    stint.get(
                        "lap_start"
                    )
                )

                or

                pd.isna(
                    stint.get(
                        "lap_end"
                    )
                )
            ):

                continue


            has_stint = True


            lap_start = int(
                stint["lap_start"]
            )

            lap_end = int(
                stint["lap_end"]
            )


            compound = str(
                stint.get(
                    "compound",
                    "UNKNOWN"
                )
            ).upper()


            if compound in (
                "NAN",
                "NONE",
                ""
            ):

                compound = "UNKNOWN"


            ax2.hlines(

                y=y_idx,

                xmin=lap_start,

                xmax=lap_end,

                linewidth=12,

                color=compound_colors.get(
                    compound,
                    "black"
                ),

                alpha=0.85
            )


            ax2.text(

                (
                    lap_start
                    +
                    lap_end
                )
                /
                2,

                y_idx,

                compound[0],

                ha="center",

                va="center",

                fontsize=8,

                fontweight="bold"
            )


    if not has_stint:

        ax2.hlines(

            y=y_idx,

            xmin=1,

            xmax=MAX_LAP,

            linewidth=3,

            color=driver_colors[
                driver_num
            ],

            alpha=0.5
        )


    if not pit.empty:

        dp = pit[

            pit["driver_number"]
            .eq(driver_num)

        ].sort_values(
            "lap_number"
        )


        for _, stop in dp.iterrows():

            if pd.isna(
                stop["lap_number"]
            ):
                continue


            pit_lap = int(
                stop["lap_number"]
            )


            ax2.scatter(

                pit_lap,
                y_idx,

                marker="v",

                s=95,

                color="black",

                zorder=20
            )


            if (
                "StopTime" in stop.index

                and

                pd.notna(
                    stop["StopTime"]
                )
            ):

                ax2.text(

                    pit_lap,

                    y_idx - 0.27,

                    f"{stop['StopTime']:.1f}s",

                    ha="center",

                    va="center",

                    fontsize=7,

                    fontweight="bold"
                )


ax2.set_yticks(
    yticks
)


ax2.set_yticklabels(
    ylabels
)


ax2.invert_yaxis()


ax2.set_xlabel(
    "Race Lap"
)

ax2.set_ylabel(
    "Top 10"
)


ax2.set_title(

    "Tyre Strategy & Pit Stops\n"
    "▼ = Pit Stop | "
    "S = Soft | M = Medium | H = Hard",

    fontsize=13,

    fontweight="bold"
)


ax2.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


ax2.set_xlim(
    1,
    MAX_LAP + 1
)


# ================================================================
# LEGEND
# ================================================================

used_compounds = []


if (
    not stints.empty

    and

    "compound" in stints.columns
):

    used_compounds = (

        stints["compound"]

        .dropna()

        .astype(str)

        .str.upper()

        .unique()

        .tolist()
    )


legend_elements = []


for compound in used_compounds:

    if compound in (
        "NAN",
        "NONE",
        ""
    ):

        continue


    legend_elements.append(

        Line2D(
            [0], [0],

            color=compound_colors.get(
                compound,
                "black"
            ),

            lw=8,

            label=compound
        )
    )


legend_elements.append(

    Line2D(
        [0], [0],

        marker="v",

        color="black",

        linestyle="None",

        markersize=8,

        label="Pit Stop"
    )
)


ax2.legend(

    handles=legend_elements,

    loc="upper center",

    bbox_to_anchor=(
        0.5,
        -0.14
    ),

    ncol=max(
        1,
        len(legend_elements)
    )
)


plt.tight_layout()

plt.show()


# ================================================================
# PIT TABLE
# ================================================================

print()
print("=" * 80)
print("TOP 10 PIT STOP DETAILS")
print("=" * 80)


if pit.empty:

    print(
        "Tidak ada pit-stop data."
    )


else:

    pit_table = (
        pit.copy()
    )


    pit_table["Driver"] = (
        pit_table["driver_number"]
        .map(driver_map)
    )


    finish_map = (

        top10
        .set_index("driver_number")
        ["position"]
        .to_dict()
    )


    pit_table["Finish"] = (
        pit_table["driver_number"]
        .map(finish_map)
    )


    wanted = [
        "Finish",
        "Driver",
        "lap_number",
        "StopTime",
        "lane_duration"
    ]


    existing = [

        c

        for c in wanted

        if c in pit_table.columns
    ]


    pit_display = (

        pit_table[existing]

        .sort_values(
            [
                "Finish",
                "lap_number"
            ]
        )

        .rename(
            columns={
                "lap_number":
                    "Pit Lap",

                "StopTime":
                    "Stop Time (s)",

                "lane_duration":
                    "Pit Lane Time (s)"
            }
        )
    )


    display(
        pit_display
    )
