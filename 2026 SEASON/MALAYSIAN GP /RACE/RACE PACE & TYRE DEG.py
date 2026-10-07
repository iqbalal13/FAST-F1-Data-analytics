# ================================================================
# F1 SEPANG / KUALA LUMPUR 2026
# TOP 10 RACE PACE + PIT STOP / TYRE STRATEGY
# OPENF1 - GOOGLE COLAB - ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# ================================================================
# CONFIG
# ================================================================

YEAR = 2026
BASE = "https://api.openf1.org/v1"


# ================================================================
# API HELPER
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
        print("\nAPI ERROR")
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


# ================================================================
# DATETIME HELPER
# ================================================================

def parse_dt(x):

    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


# ================================================================
# 1. FIND SEPANG RACE SESSION
# ================================================================

print("=" * 75)
print("SEARCHING SEPANG / KUALA LUMPUR 2026 RACE")
print("=" * 75)

sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)


location_series = (
    sessions["location"]
    if "location" in sessions.columns
    else pd.Series("", index=sessions.index)
)

circuit_series = (
    sessions["circuit_short_name"]
    if "circuit_short_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)


sepang_mask = (

    location_series
    .astype(str)
    .str.contains(
        "Kuala Lumpur|Sepang",
        case=False,
        regex=True,
        na=False
    )

    |

    circuit_series
    .astype(str)
    .str.contains(
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
        "Race Sepang / Kuala Lumpur 2026 tidak ditemukan."
    )


race_sessions["parsed_start"] = parse_dt(
    race_sessions["date_start"]
)

race_sessions = race_sessions.sort_values(
    "parsed_start"
)


race_session = race_sessions.iloc[-1]


SESSION_KEY = int(
    race_session["session_key"]
)


print("Session :", race_session["session_name"])
print("Location:", race_session["location"])
print("Circuit :", race_session["circuit_short_name"])
print("Key     :", SESSION_KEY)


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
# 3. OFFICIAL SESSION RESULT -> TOP 10
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
    results["position"].between(1, 10)
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
    top10["driver_number"].astype(str)
)


TOP10_NUMBERS = (
    top10["driver_number"]
    .tolist()
)


print("\n" + "=" * 75)
print("TOP 10 FINISHERS")
print("=" * 75)

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
# 4. LOAD ALL RACE LAPS
# ================================================================

laps = pd.DataFrame(
    api_get(
        "laps",
        {"session_key": SESSION_KEY}
    )
)


numeric_cols = [
    "driver_number",
    "lap_number",
    "lap_duration"
]


for col in numeric_cols:

    laps[col] = pd.to_numeric(
        laps[col],
        errors="coerce"
    )


laps = laps[
    laps["driver_number"].isin(
        TOP10_NUMBERS
    )
].copy()


# ================================================================
# 5. LOAD PIT STOPS
# ================================================================

pit_data = api_get(
    "pit",
    {"session_key": SESSION_KEY},
    allow_empty=True
)


pit = pd.DataFrame(
    pit_data
)


if not pit.empty:

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
        pit["driver_number"].isin(
            TOP10_NUMBERS
        )
    ].copy()


    # stationary stop time
    if "stop_duration" in pit.columns:

        pit["StopTime"] = (
            pit["stop_duration"]
        )

    else:

        pit["StopTime"] = np.nan


    # fallback kalau stop_duration tidak tersedia
    if "lane_duration" in pit.columns:

        pit["StopTime"] = (
            pit["StopTime"]
            .fillna(
                pit["lane_duration"]
            )
        )


else:

    pit = pd.DataFrame(
        columns=[
            "driver_number",
            "lap_number",
            "StopTime"
        ]
    )


# ================================================================
# 6. LOAD STINT / COMPOUND DATA
# ================================================================

stint_data = api_get(
    "stints",
    {"session_key": SESSION_KEY},
    allow_empty=True
)


stints = pd.DataFrame(
    stint_data
)


if not stints.empty:

    for col in [
        "driver_number",
        "lap_start",
        "lap_end",
        "stint_number"
    ]:

        stints[col] = pd.to_numeric(
            stints[col],
            errors="coerce"
        )


    stints = stints[
        stints["driver_number"].isin(
            TOP10_NUMBERS
        )
    ].copy()


# ================================================================
# 7. CLEAN RACE PACE
# ================================================================

pace_frames = []


for _, result_row in top10.iterrows():

    driver_num = int(
        result_row["driver_number"]
    )


    d = laps[
        laps["driver_number"]
        ==
        driver_num
    ].copy()


    # lap time valid
    d = d.dropna(
        subset=[
            "lap_number",
            "lap_duration"
        ]
    )


    d = d[
        d["lap_duration"] > 0
    ]


    # Lap 1 tidak cocok untuk pure race pace
    d = d[
        d["lap_number"] > 1
    ]


    # Buang pit-out laps
    if "is_pit_out_lap" in d.columns:

        d = d[
            d["is_pit_out_lap"] != True
        ]


    # --------------------------------
    # buang in-lap yang masuk pit
    # --------------------------------

    if not pit.empty:

        driver_pits = pit[
            pit["driver_number"]
            ==
            driver_num
        ]


        pit_laps = (
            driver_pits["lap_number"]
            .dropna()
            .astype(int)
            .tolist()
        )


        d = d[
            ~d["lap_number"].isin(
                pit_laps
            )
        ]


    if d.empty:
        continue


    # --------------------------------
    # remove extreme slow laps
    #
    # median + 8 seconds
    # mengurangi SC / traffic / incidents
    # --------------------------------

    median_time = d[
        "lap_duration"
    ].median()


    d = d[
        d["lap_duration"]
        <=
        median_time + 8
    ].copy()


    # --------------------------------
    # 3-LAP ROLLING MEDIAN
    # --------------------------------

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


    d["Driver"] = result_row[
        "Driver"
    ]


    d["Position"] = int(
        result_row[
            "position"
        ]
    )


    pace_frames.append(
        d
    )


pace = pd.concat(
    pace_frames,
    ignore_index=True
)


# ================================================================
# 8. SUMMARY PACE
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


# pit count
if not pit.empty:

    pit_count = (

        pit
        .groupby(
            "driver_number"
        )
        .size()
        .rename(
            "PitStops"
        )

    )


    pace_summary["PitStops"] = (

        pace_summary[
            "driver_number"
        ]
        .map(
            pit_count
        )
        .fillna(0)
        .astype(int)

    )

else:

    pace_summary["PitStops"] = 0


print("\n" + "=" * 75)
print("RACE PACE SUMMARY")
print("=" * 75)


summary_display = (
    pace_summary.copy()
)


summary_display["MedianPace"] = (
    summary_display["MedianPace"]
    .map(
        lambda x:
        f"{x:.3f}s"
    )
)


summary_display["MeanPace"] = (
    summary_display["MeanPace"]
    .map(
        lambda x:
        f"{x:.3f}s"
    )
)


display(
    summary_display[
        [
            "Position",
            "Driver",
            "MedianPace",
            "MeanPace",
            "PitStops"
        ]
    ]
)


# ================================================================
# 9. CREATE FIGURE
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
            [2.2, 1.2]
    },

    sharex=True

)


# ================================================================
# DRIVER COLORS
# ================================================================

cmap = plt.colormaps["tab10"]


driver_colors = {

    int(row["driver_number"]):
        cmap(i)

    for i, (_, row)
    in enumerate(
        top10.iterrows()
    )

}


# ================================================================
# 10. TOP GRAPH — RACE PACE
# ================================================================

for _, result_row in top10.iterrows():

    driver_num = int(
        result_row["driver_number"]
    )

    driver = result_row[
        "Driver"
    ]

    position = int(
        result_row[
            "position"
        ]
    )


    d = pace[
        pace["driver_number"]
        ==
        driver_num
    ]


    if d.empty:
        continue


    color = driver_colors[
        driver_num
    ]


    ax1.plot(

        d["lap_number"],

        d["RacePace"],

        linewidth=2,

        color=color,

        label=
        f"P{position} {driver}"

    )


    # ============================================================
    # PIT MARKERS ON PACE GRAPH
    # ============================================================

    if not pit.empty:

        dp = pit[
            pit["driver_number"]
            ==
            driver_num
        ]


        for _, stop in dp.iterrows():

            if pd.isna(
                stop["lap_number"]
            ):
                continue


            pit_lap = int(
                stop["lap_number"]
            )


            # cari pace point terdekat
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


# ================================================================
# RACE PACE STYLE
# ================================================================

ax1.set_title(

    "SEPANG 2026 — TOP 10 RACE PACE + PIT STOPS\n"
    "3-Lap Rolling Median | Lower = Faster",

    fontsize=16,

    fontweight="bold",

    pad=16

)


ax1.set_ylabel(
    "Lap Time / Race Pace (seconds)"
)


ax1.grid(
    alpha=0.25,
    linestyle="--"
)


ax1.legend(

    ncol=5,

    fontsize=9,

    loc="upper center",

    bbox_to_anchor=(
        0.5,
        1.0
    )

)


# ================================================================
# 11. BOTTOM GRAPH — STINT / PIT STRATEGY
# ================================================================

compound_colors = {

    "SOFT":
        "red",

    "MEDIUM":
        "gold",

    "HARD":
        "lightgray",

    "INTERMEDIATE":
        "green",

    "WET":
        "blue",

    "UNKNOWN":
        "black"

}


MAX_LAP = int(
    laps[
        "lap_number"
    ].max()
)


yticks = []
ylabels = []


for y, (_, result_row) in enumerate(
    top10.iterrows()
):

    driver_num = int(
        result_row[
            "driver_number"
        ]
    )


    driver = result_row[
        "Driver"
    ]


    position = int(
        result_row[
            "position"
        ]
    )


    yticks.append(
        y
    )


    ylabels.append(
        f"P{position} {driver}"
    )


    # ============================================================
    # STINT BARS
    # ============================================================

    driver_has_stint = False


    if not stints.empty:

        ds = stints[
            stints[
                "driver_number"
            ]
            ==
            driver_num
        ].sort_values(
            "stint_number"
        )


        for _, stint in ds.iterrows():

            if (
                pd.isna(
                    stint["lap_start"]
                )
                or
                pd.isna(
                    stint["lap_end"]
                )
            ):
                continue


            driver_has_stint = True


            lap_start = int(
                stint[
                    "lap_start"
                ]
            )


            lap_end = int(
                stint[
                    "lap_end"
                ]
            )


            compound = str(
                stint.get(
                    "compound",
                    "UNKNOWN"
                )
            ).upper()


            tyre_color = (
                compound_colors.get(
                    compound,
                    "black"
                )
            )


            ax2.hlines(

                y=y,

                xmin=lap_start,

                xmax=lap_end,

                linewidth=12,

                color=tyre_color,

                alpha=0.85

            )


            # compound text
            mid_lap = (
                lap_start
                +
                lap_end
            ) / 2


            ax2.text(

                mid_lap,
                y,

                compound[0],

                ha="center",
                va="center",

                fontsize=8,

                fontweight="bold",

                color="black"

            )


    # fallback kalau stint endpoint kosong
    if not driver_has_stint:

        ax2.hlines(

            y=y,

            xmin=1,

            xmax=MAX_LAP,

            linewidth=3,

            color=driver_colors[
                driver_num
            ],

            alpha=0.5

        )


    # ============================================================
    # PIT STOP MARKERS
    # ============================================================

    if not pit.empty:

        dp = pit[
            pit[
                "driver_number"
            ]
            ==
            driver_num
        ].sort_values(
            "lap_number"
        )


        for _, stop in dp.iterrows():

            if pd.isna(
                stop["lap_number"]
            ):
                continue


            pit_lap = int(
                stop[
                    "lap_number"
                ]
            )


            ax2.scatter(

                pit_lap,
                y,

                marker="v",

                s=100,

                color="black",

                zorder=20

            )


            # stop duration
            if pd.notna(
                stop[
                    "StopTime"
                ]
            ):

                ax2.text(

                    pit_lap,
                    y - 0.27,

                    f"{stop['StopTime']:.1f}s",

                    ha="center",
                    va="center",

                    fontsize=7,

                    fontweight="bold"

                )


# ================================================================
# 12. STRATEGY GRAPH STYLE
# ================================================================

ax2.set_yticks(
    yticks
)


ax2.set_yticklabels(
    ylabels
)


# P1 di atas
ax2.invert_yaxis()


ax2.set_xlabel(
    "Race Lap"
)


ax2.set_ylabel(
    "Top 10"
)


ax2.set_title(

    "Tyre Stints & Pit Stops\n"
    "▼ = Pit Stop | Number = Stationary Stop Time",

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
# 13. COMPOUND LEGEND
# ================================================================

used_compounds = []


if not stints.empty:

    used_compounds = (

        stints[
            "compound"
        ]
        .dropna()
        .astype(str)
        .str.upper()
        .unique()
        .tolist()

    )


legend_elements = []


for compound in used_compounds:

    legend_elements.append(

        Line2D(

            [0],
            [0],

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

        [0],
        [0],

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
        -0.12
    ),

    ncol=max(
        1,
        len(
            legend_elements
        )
    )

)


plt.tight_layout()

plt.show()


# ================================================================
# 14. PIT STOP TABLE
# ================================================================

print("\n" + "=" * 75)
print("TOP 10 PIT STOP DETAILS")
print("=" * 75)


if pit.empty:

    print(
        "Tidak ada pit-stop data."
    )

else:

    pit_table = pit.copy()


    pit_table["Driver"] = (
        pit_table[
            "driver_number"
        ]
        .map(
            driver_map
        )
    )


    position_map = (

        top10
        .set_index(
            "driver_number"
        )
        ["position"]
        .to_dict()

    )


    pit_table["Position"] = (

        pit_table[
            "driver_number"
        ]
        .map(
            position_map
        )

    )


    pit_table = pit_table.sort_values(
        [
            "Position",
            "lap_number"
        ]
    )


    display(

        pit_table[
            [
                "Position",
                "Driver",
                "lap_number",
                "StopTime",
                "lane_duration"
            ]
        ].rename(
            columns={
                "Position":
                    "Finish",

                "lap_number":
                    "Pit Lap",

                "StopTime":
                    "Stop Time (s)",

                "lane_duration":
                    "Pit Lane Time (s)"
            }
        )

    )
