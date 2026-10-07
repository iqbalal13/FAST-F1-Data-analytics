# ================================================================
# F1 SEPANG / KUALA LUMPUR 2026
# TOP 10 — TYRE DEGRADATION + AVERAGE PACE PER STINT
# OPENF1
# GOOGLE COLAB — ONE CELL
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
# API
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
# LAP TIME FORMAT
# ================================================================

def format_laptime(seconds):

    if pd.isna(seconds):
        return "-"

    minutes = int(seconds // 60)
    secs = seconds % 60

    return f"{minutes}:{secs:06.3f}"


# ================================================================
# 1. FIND SEPANG RACE
# ================================================================

print("=" * 75)
print("SEARCH SEPANG / KUALA LUMPUR 2026 RACE")
print("=" * 75)

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
        "Race Sepang 2026 tidak ditemukan."
    )


race_sessions["parsed_start"] = parse_dt(
    race_sessions["date_start"]
)


race_sessions = race_sessions.sort_values(
    "parsed_start"
)


session = race_sessions.iloc[-1]


SESSION_KEY = int(
    session["session_key"]
)


print()
print("Race found")
print("Location :", session["location"])
print("Circuit  :", session["circuit_short_name"])
print("Session  :", SESSION_KEY)


# ================================================================
# 2. DRIVER DATA
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
# 3. TOP 10 FINISH RESULT
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
        top10[
            "driver_number"
        ].astype(str)
    )
)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


print("\n" + "=" * 75)
print("TOP 10")
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


laps = laps[
    laps["driver_number"]
    .isin(TOP10)
].copy()


# ================================================================
# 5. LOAD STINTS
# ================================================================

stints = pd.DataFrame(
    api_get(
        "stints",
        {
            "session_key":
                SESSION_KEY
        }
    )
)


for col in [
    "driver_number",
    "stint_number",
    "lap_start",
    "lap_end",
    "tyre_age_at_start"
]:

    stints[col] = pd.to_numeric(
        stints[col],
        errors="coerce"
    )


stints = stints[
    stints["driver_number"]
    .isin(TOP10)
].copy()


stints["tyre_age_at_start"] = (

    stints[
        "tyre_age_at_start"
    ]
    .fillna(0)

)


# ================================================================
# 6. PIT DATA
# ================================================================

pit_data = api_get(
    "pit",
    {
        "session_key":
            SESSION_KEY
    },
    allow_empty=True
)


pit = pd.DataFrame(
    pit_data
)


if not pit.empty:

    pit["driver_number"] = pd.to_numeric(
        pit["driver_number"],
        errors="coerce"
    )

    pit["lap_number"] = pd.to_numeric(
        pit["lap_number"],
        errors="coerce"
    )


    pit = pit[
        pit["driver_number"]
        .isin(TOP10)
    ].copy()


# ================================================================
# 7. COMPOUND COLORS
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


line_styles = [
    "-",
    "--",
    "-.",
    ":"
]


# ================================================================
# 8. PROCESS EACH STINT
# ================================================================

clean_lap_frames = []
summary_rows = []


for _, result_row in top10.iterrows():

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


    driver_stints = stints[

        stints["driver_number"]
        ==
        driver_num

    ].sort_values(
        "stint_number"
    )


    # pit laps driver
    driver_pit_laps = []

    if not pit.empty:

        driver_pit_laps = (

            pit[
                pit["driver_number"]
                ==
                driver_num
            ]["lap_number"]

            .dropna()

            .astype(int)

            .tolist()

        )


    for _, stint in driver_stints.iterrows():

        if (
            pd.isna(stint["lap_start"])
            or
            pd.isna(stint["lap_end"])
        ):
            continue


        stint_number = int(
            stint["stint_number"]
        )

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


        tyre_age_start = float(
            stint[
                "tyre_age_at_start"
            ]
        )


        # ========================================================
        # LAPS IN THIS STINT
        # ========================================================

        s = laps[

            (
                laps["driver_number"]
                ==
                driver_num
            )

            &

            (
                laps["lap_number"]
                >=
                lap_start
            )

            &

            (
                laps["lap_number"]
                <=
                lap_end
            )

        ].copy()


        # valid lap time
        s = s.dropna(
            subset=[
                "lap_number",
                "lap_duration"
            ]
        )


        s = s[
            s["lap_duration"] > 0
        ]


        # ========================================================
        # REMOVE RACE LAP 1
        # Standing-start lap bukan representasi pace
        # ========================================================

        s = s[
            s["lap_number"] > 1
        ]


        # ========================================================
        # REMOVE PIT-OUT
        # ========================================================

        if "is_pit_out_lap" in s.columns:

            s = s[
                s["is_pit_out_lap"]
                != True
            ]


        # ========================================================
        # REMOVE PIT-IN LAP
        # ========================================================

        if driver_pit_laps:

            s = s[

                ~s["lap_number"]
                .astype(int)
                .isin(
                    driver_pit_laps
                )

            ]


        if len(s) < 2:
            continue


        # ========================================================
        # TYRE AGE
        #
        # age at start of current lap
        # ========================================================

        s["TyreAge"] = (

            tyre_age_start

            +

            (
                s["lap_number"]
                -
                lap_start
            )

        )


        # ========================================================
        # ROBUST OUTLIER REMOVAL
        #
        # MAD = Median Absolute Deviation
        #
        # Helps remove:
        # - SC laps
        # - VSC-ish extreme laps
        # - traffic
        # - mistakes
        # - yellow flag
        # ========================================================

        median = (
            s["lap_duration"]
            .median()
        )


        mad = np.median(

            np.abs(

                s["lap_duration"]

                -

                median

            )

        )


        robust_sigma = (
            1.4826 * mad
        )


        # minimum tolerance 2.5 sec
        threshold = max(
            3.5 * robust_sigma,
            2.5
        )


        s = s[

            np.abs(
                s["lap_duration"]
                -
                median
            )
            <=
            threshold

        ].copy()


        if len(s) < 2:
            continue


        # ========================================================
        # STINT STATS
        # ========================================================

        average_pace = (
            s["lap_duration"]
            .mean()
        )


        median_pace = (
            s["lap_duration"]
            .median()
        )


        best_pace = (
            s["lap_duration"]
            .min()
        )


        # delta relative to best lap of this stint
        s["DeltaToBest"] = (

            s["lap_duration"]

            -

            best_pace

        )


        # ========================================================
        # DEGRADATION SLOPE
        #
        # y = lap time
        # x = tyre age
        #
        # slope unit = seconds / lap
        # ========================================================

        deg_slope = np.nan
        intercept = np.nan


        if (
            len(s) >= 4
            and
            s["TyreAge"].nunique() >= 4
        ):

            slope, intercept = np.polyfit(

                s["TyreAge"],

                s["lap_duration"],

                1

            )

            deg_slope = float(
                slope
            )


        # ========================================================
        # SAVE CLEAN LAPS
        # ========================================================

        s["Driver"] = driver
        s["Position"] = position
        s["Stint"] = stint_number
        s["Compound"] = compound
        s["DegSlope"] = deg_slope


        clean_lap_frames.append(
            s
        )


        # ========================================================
        # SUMMARY
        # ========================================================

        summary_rows.append({

            "Position":
                position,

            "Driver":
                driver,

            "DriverNumber":
                driver_num,

            "Stint":
                stint_number,

            "Compound":
                compound,

            "LapStart":
                lap_start,

            "LapEnd":
                lap_end,

            "TyreAgeStart":
                tyre_age_start,

            "ValidLaps":
                len(s),

            "AveragePace":
                average_pace,

            "MedianPace":
                median_pace,

            "BestLap":
                best_pace,

            "DegSlope":
                deg_slope

        })


# ================================================================
# 9. CREATE DATAFRAMES
# ================================================================

if not clean_lap_frames:

    raise RuntimeError(
        "Tidak ada clean stint lap data."
    )


clean_laps = pd.concat(
    clean_lap_frames,
    ignore_index=True
)


summary = pd.DataFrame(
    summary_rows
)


summary = summary.sort_values(
    [
        "Position",
        "Stint"
    ]
).reset_index(
    drop=True
)


# ================================================================
# 10. FORMATTED TABLE
# ================================================================

display_summary = summary.copy()


display_summary[
    "Average Pace"
] = (
    display_summary[
        "AveragePace"
    ]
    .apply(
        format_laptime
    )
)


display_summary[
    "Median Pace"
] = (
    display_summary[
        "MedianPace"
    ]
    .apply(
        format_laptime
    )
)


display_summary[
    "Best Lap"
] = (
    display_summary[
        "BestLap"
    ]
    .apply(
        format_laptime
    )
)


display_summary[
    "Deg / Lap"
] = (

    display_summary[
        "DegSlope"
    ]
    .apply(
        lambda x:
        f"{x:+.3f} s/lap"
        if pd.notna(x)
        else "-"
    )

)


print("\n" + "=" * 95)
print("TOP 10 — TYRE DEGRADATION & STINT PACE")
print("=" * 95)


display(

    display_summary[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "ValidLaps",
            "Average Pace",
            "Median Pace",
            "Best Lap",
            "Deg / Lap"
        ]
    ]

)


# ================================================================
# 11. TYRE DEGRADATION GRAPH
#
# 10 DRIVERS
# 5 ROW x 2 COLUMN
# ================================================================

fig, axes = plt.subplots(

    5,
    2,

    figsize=(17, 24)

)


axes = axes.flatten()


for plot_index, (_, result_row) in enumerate(
    top10.iterrows()
):

    ax = axes[
        plot_index
    ]


    driver = result_row[
        "Driver"
    ]

    position = int(
        result_row[
            "position"
        ]
    )


    driver_data = clean_laps[

        clean_laps["Driver"]
        ==
        driver

    ]


    driver_summary = summary[

        summary["Driver"]
        ==
        driver

    ]


    for _, sr in driver_summary.iterrows():

        stint_num = int(
            sr["Stint"]
        )

        compound = sr[
            "Compound"
        ]

        color = compound_colors.get(
            compound,
            "black"
        )


        style = line_styles[
            (stint_num - 1)
            %
            len(line_styles)
        ]


        s = driver_data[

            driver_data["Stint"]
            ==
            stint_num

        ].sort_values(
            "TyreAge"
        )


        # --------------------------------
        # raw clean laps
        # --------------------------------

        ax.scatter(

            s["TyreAge"],

            s["DeltaToBest"],

            color=color,

            s=32,

            alpha=0.75

        )


        # --------------------------------
        # regression
        # --------------------------------

        if (
            pd.notna(
                sr["DegSlope"]
            )
            and
            len(s) >= 4
        ):

            x_fit = np.linspace(

                s["TyreAge"].min(),

                s["TyreAge"].max(),

                50

            )


            slope, intercept = np.polyfit(

                s["TyreAge"],

                s["DeltaToBest"],

                1

            )


            y_fit = (

                slope
                *
                x_fit

                +

                intercept

            )


            ax.plot(

                x_fit,

                y_fit,

                color=color,

                linestyle=style,

                linewidth=2,

                label=(
                    f"S{stint_num} "
                    f"{compound} "
                    f"{sr['DegSlope']:+.3f}s/lap"
                )

            )


        else:

            ax.plot(

                s["TyreAge"],

                s["DeltaToBest"],

                color=color,

                linestyle=style,

                linewidth=1.5,

                label=(
                    f"S{stint_num} "
                    f"{compound}"
                )

            )


    ax.axhline(
        0,
        linewidth=0.8,
        alpha=0.4
    )


    ax.set_title(

        f"P{position} — {driver}",

        fontsize=13,

        fontweight="bold"

    )


    ax.set_xlabel(
        "Tyre Age (laps)"
    )


    ax.set_ylabel(
        "Lap Time Delta to Stint Best (s)"
    )


    ax.grid(
        alpha=0.2,
        linestyle="--"
    )


    ax.legend(
        fontsize=8
    )


fig.suptitle(

    "SEPANG 2026 — TOP 10 TYRE DEGRADATION\n"
    "Clean Race Laps | Positive Slope = Lap Time Increasing",

    fontsize=18,

    fontweight="bold",

    y=1.005

)


plt.tight_layout()

plt.show()


# ================================================================
# 12. AVERAGE PACE PER STINT GRAPH
# ================================================================

plot_summary = summary.copy()


plot_summary["Label"] = (

    "P"
    +
    plot_summary[
        "Position"
    ].astype(int).astype(str)

    +
    " "

    +
    plot_summary[
        "Driver"
    ]

    +
    " — S"

    +
    plot_summary[
        "Stint"
    ].astype(int).astype(str)

    +
    " "

    +
    plot_summary[
        "Compound"
    ]

)


# reverse for horizontal plot
plot_summary = plot_summary.iloc[::-1]


bar_colors = [

    compound_colors.get(
        compound,
        "black"
    )

    for compound
    in plot_summary[
        "Compound"
    ]

]


fig, ax = plt.subplots(
    figsize=(14, 12)
)


bars = ax.barh(

    plot_summary[
        "Label"
    ],

    plot_summary[
        "AveragePace"
    ],

    color=bar_colors,

    alpha=0.85

)


# ================================================================
# 13. ZOOM X AXIS
#
# Biar selisih pace terlihat.
# ================================================================

min_pace = (
    plot_summary[
        "AveragePace"
    ].min()
)


max_pace = (
    plot_summary[
        "AveragePace"
    ].max()
)


ax.set_xlim(

    min_pace - 1.0,

    max_pace + 1.5

)


# ================================================================
# 14. LABEL AVERAGE + DEG
# ================================================================

for bar, (_, row) in zip(

    bars,

    plot_summary.iterrows()

):

    pace_text = format_laptime(
        row["AveragePace"]
    )


    deg_text = (

        f"{row['DegSlope']:+.3f}s/lap"

        if pd.notna(
            row["DegSlope"]
        )

        else "-"

    )


    ax.text(

        row["AveragePace"]
        +
        0.05,

        bar.get_y()
        +
        bar.get_height() / 2,

        f"{pace_text} | deg {deg_text}",

        va="center",

        fontsize=8,

        fontweight="bold"

    )


ax.set_title(

    "SEPANG 2026 — AVERAGE RACE PACE PER STINT\n"
    "Lower = Faster",

    fontsize=16,

    fontweight="bold",

    pad=16

)


ax.set_xlabel(
    "Average Clean Lap Time (seconds)"
)


ax.set_ylabel(
    "Driver / Stint / Compound"
)


ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


plt.tight_layout()

plt.show()


# ================================================================
# 15. DEGRADATION RANKING
# ================================================================

deg_ranking = summary[
    summary["DegSlope"].notna()
].copy()


deg_ranking = deg_ranking.sort_values(
    "DegSlope"
)


print("\n" + "=" * 95)
print("TYRE DEGRADATION SLOPE — LOWEST TO HIGHEST")
print("=" * 95)


deg_table = deg_ranking[
    [
        "Position",
        "Driver",
        "Stint",
        "Compound",
        "ValidLaps",
        "AveragePace",
        "DegSlope"
    ]
].copy()


deg_table[
    "AveragePace"
] = (
    deg_table[
        "AveragePace"
    ]
    .apply(
        format_laptime
    )
)


deg_table[
    "DegSlope"
] = (
    deg_table[
        "DegSlope"
    ]
    .map(
        lambda x:
        f"{x:+.3f} s/lap"
    )
)


display(
    deg_table
)
