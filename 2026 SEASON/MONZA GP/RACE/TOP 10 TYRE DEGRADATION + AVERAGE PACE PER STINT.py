# ================================================================
# ITALIAN GP 2026 — MONZA
# TOP 10 TYRE DEGRADATION + AVERAGE PACE PER STINT
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

LAST_REQUEST_TIME = time.time()
MIN_REQUEST_INTERVAL = 1.10


# ================================================================
# HTTP
# ================================================================

http = requests.Session()

http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})


# ================================================================
# SAFE OPENF1 API
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
                f"Retry in {wait}s..."
            )

            time.sleep(wait)

            continue


        # --------------------------------------------------------
        # 429
        # --------------------------------------------------------

        if r.status_code == 429:

            retry_after = r.headers.get(
                "Retry-After"
            )

            if retry_after:

                try:

                    wait = float(
                        retry_after
                    )

                except:

                    wait = min(
                        4 + attempt * 4,
                        40
                    )

            else:

                wait = min(
                    4 + attempt * 4,
                    40
                )


            wait += random.uniform(
                0.3,
                1.0
            )


            print(
                f"⚠️ OpenF1 429 [{endpoint}] — "
                f"retry {attempt+1}/{max_retries} "
                f"in {wait:.1f}s"
            )


            time.sleep(wait)

            continue


        if r.status_code != 200:

            print()
            print("API ERROR")
            print("URL    :", r.url)
            print("Status :", r.status_code)
            print("Body   :", r.text[:500])

            raise RuntimeError(
                f"OpenF1 HTTP {r.status_code}"
            )


        data = r.json()


        if (
            not data
            and
            not allow_empty
        ):

            raise RuntimeError(
                f"No data from {endpoint}"
            )


        return data


    raise RuntimeError(
        f"OpenF1 failed: {endpoint}"
    )


# ================================================================
# HELPERS
# ================================================================

def parse_dt(x):

    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )


def format_laptime(seconds):

    if pd.isna(seconds):

        return "-"


    minutes = int(
        float(seconds) // 60
    )


    sec = (
        float(seconds)
        %
        60
    )


    return (
        f"{minutes}:"
        f"{sec:06.3f}"
    )


# ================================================================
# FIND MONZA RACE
# ================================================================

print(
    "=" * 90
)

print(
    "ITALIAN GP 2026 — MONZA"
)

print(
    "TYRE DEGRADATION + AVERAGE PACE PER STINT"
)

print(
    "=" * 90
)


sessions = pd.DataFrame(
    api_get(
        "sessions",
        {
            "year":
                YEAR
        }
    )
)


location = (
    sessions["location"]

    if "location" in sessions.columns

    else pd.Series(
        "",
        index=sessions.index
    )
)


circuit = (
    sessions["circuit_short_name"]

    if "circuit_short_name" in sessions.columns

    else pd.Series(
        "",
        index=sessions.index
    )
)


monza_mask = (

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


race_sessions = sessions[

    monza_mask

    &

    sessions["session_name"]
    .astype(str)
    .str.lower()
    .eq("race")

].copy()


if race_sessions.empty:

    raise RuntimeError(
        "Monza 2026 race tidak ditemukan."
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


print(
    "Session Key :",
    SESSION_KEY
)

print(
    "Location    :",
    race.get(
        "location",
        "Monza"
    )
)

print(
    "Circuit     :",
    race.get(
        "circuit_short_name",
        "Monza"
    )
)


# ================================================================
# DRIVERS
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
    subset=[
        "driver_number"
    ]
)


drivers["driver_number"] = (
    drivers["driver_number"]
    .astype(int)
)


drivers = (
    drivers
    .drop_duplicates(
        "driver_number"
    )
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
# TOP 10 RESULT
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
    .between(
        1,
        10
    )

].copy()


top10 = (

    top10

    .sort_values(
        "position"
    )

    .reset_index(
        drop=True
    )
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
        top10["driver_number"]
        .astype(str)
    )
)


TOP10 = (
    top10["driver_number"]
    .tolist()
)


print()
print(
    "=" * 90
)

print(
    "TOP 10 FINISHERS"
)

print(
    "=" * 90
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
# LOAD LAPS
# ================================================================

print(
    "\nLoading race laps..."
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
        "lap_duration"
    ]
)


laps = laps[

    laps["lap_duration"]
    >
    0

].copy()


print(
    "Top-10 lap records:",
    len(laps)
)


# ================================================================
# LOAD STINTS
# ================================================================

print(
    "Loading tyre stints..."
)


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

    if col in stints.columns:

        stints[col] = pd.to_numeric(
            stints[col],
            errors="coerce"
        )


if "tyre_age_at_start" not in stints.columns:

    stints["tyre_age_at_start"] = 0


stints["tyre_age_at_start"] = (
    stints["tyre_age_at_start"]
    .fillna(0)
)


if "compound" not in stints.columns:

    stints["compound"] = "UNKNOWN"


stints = stints[

    stints["driver_number"]
    .isin(
        TOP10
    )

].copy()


stints = stints.dropna(
    subset=[
        "driver_number",
        "lap_start",
        "lap_end"
    ]
)


print(
    "Top-10 stints:",
    len(stints)
)


# ================================================================
# COLORS
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
# PROCESS EACH STINT
# ================================================================

clean_frames = []

summary_rows = []


for _, result_row in (
    top10.iterrows()
):

    driver_num = int(
        result_row[
            "driver_number"
        ]
    )


    driver = (
        result_row[
            "Driver"
        ]
    )


    finish_position = int(
        result_row[
            "position"
        ]
    )


    driver_stints = stints[

        stints["driver_number"]
        .eq(
            driver_num
        )

    ].copy()


    if (
        "stint_number"
        in
        driver_stints.columns
    ):

        driver_stints = (
            driver_stints
            .sort_values(
                "stint_number"
            )
        )

    else:

        driver_stints = (
            driver_stints
            .sort_values(
                "lap_start"
            )
        )


    driver_stints = (
        driver_stints
        .reset_index(
            drop=True
        )
    )


    number_of_stints = (
        len(
            driver_stints
        )
    )


    for stint_idx, stint in (
        driver_stints.iterrows()
    ):

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


        if (
            "stint_number"
            in
            stint.index

            and

            pd.notna(
                stint[
                    "stint_number"
                ]
            )
        ):

            stint_number = int(
                stint[
                    "stint_number"
                ]
            )

        else:

            stint_number = (
                stint_idx + 1
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

            compound = (
                "UNKNOWN"
            )


        tyre_age_start = float(
            stint.get(
                "tyre_age_at_start",
                0
            )
        )


        if pd.isna(
            tyre_age_start
        ):

            tyre_age_start = 0


        # --------------------------------------------------------
        # STINT LAPS
        # --------------------------------------------------------

        s = laps[

            laps["driver_number"]
            .eq(
                driver_num
            )

            &

            laps["lap_number"]
            .between(
                lap_start,
                lap_end
            )

        ].copy()


        s = s[

            (s["lap_number"] > 1)

            &

            (s["lap_duration"] > 0)

        ].copy()


        # pit-out
        if (
            "is_pit_out_lap"
            in
            s.columns
        ):

            s = s[
                s["is_pit_out_lap"]
                != True
            ].copy()


        # --------------------------------------------------------
        # PIT-IN LAP
        #
        # Remove last lap of every non-final stint.
        # --------------------------------------------------------

        if (
            stint_idx
            !=
            number_of_stints - 1
        ):

            s = s[

                s["lap_number"]
                !=
                lap_end

            ].copy()


        if len(s) < 2:

            continue


        # --------------------------------------------------------
        # TYRE AGE
        # --------------------------------------------------------

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
        # ROBUST OUTLIER FILTER — MAD
        # ========================================================

        median_laptime = (
            s["lap_duration"]
            .median()
        )


        mad = np.median(

            np.abs(

                s["lap_duration"]

                -

                median_laptime

            )

        )


        robust_sigma = (
            1.4826
            *
            mad
        )


        threshold = max(

            3.5
            *
            robust_sigma,

            2.5

        )


        clean = s[

            np.abs(

                s["lap_duration"]

                -

                median_laptime

            )

            <=
            threshold

        ].copy()


        if len(clean) < 2:

            continue


        # ========================================================
        # STATS
        # ========================================================

        average_pace = (
            clean["lap_duration"]
            .mean()
        )


        median_pace = (
            clean["lap_duration"]
            .median()
        )


        best_lap = (
            clean["lap_duration"]
            .min()
        )


        clean["DeltaToBest"] = (

            clean["lap_duration"]

            -

            best_lap

        )


        # ========================================================
        # DEGRADATION
        # ========================================================

        deg_slope = np.nan


        if (
            len(clean) >= 4

            and

            clean["TyreAge"]
            .nunique()
            >= 4
        ):

            slope, intercept = (
                np.polyfit(

                    clean[
                        "TyreAge"
                    ],

                    clean[
                        "lap_duration"
                    ],

                    1
                )
            )


            deg_slope = float(
                slope
            )


        clean[
            "Driver"
        ] = driver


        clean[
            "Position"
        ] = finish_position


        clean[
            "Stint"
        ] = stint_number


        clean[
            "Compound"
        ] = compound


        clean[
            "DegSlope"
        ] = deg_slope


        clean_frames.append(
            clean
        )


        summary_rows.append({

            "Position":
                finish_position,

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
                len(clean),

            "AveragePace":
                average_pace,

            "MedianPace":
                median_pace,

            "BestLap":
                best_lap,

            "DegSlope":
                deg_slope
        })


# ================================================================
# DATAFRAMES
# ================================================================

if not clean_frames:

    raise RuntimeError(
        "Tidak ada valid clean stint data."
    )


clean_laps = pd.concat(
    clean_frames,
    ignore_index=True
)


summary = pd.DataFrame(
    summary_rows
)


summary = (

    summary

    .sort_values(
        [
            "Position",
            "Stint"
        ]
    )

    .reset_index(
        drop=True
    )
)


# ================================================================
# TABLE
# ================================================================

display_summary = (
    summary.copy()
)


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


print()
print(
    "=" * 105
)

print(
    "MONZA 2026 — TYRE DEGRADATION & AVERAGE STINT PACE"
)

print(
    "=" * 105
)


display(

    display_summary[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "TyreAgeStart",
            "ValidLaps",
            "Average Pace",
            "Median Pace",
            "Best Lap",
            "Deg / Lap"
        ]
    ]

)


# ================================================================
# GRAPH 1
# TOP 10 TYRE DEGRADATION
# ================================================================

fig, axes = plt.subplots(

    5,
    2,

    figsize=(
        18,
        24
    )

)


axes = (
    axes.flatten()
)


for graph_index, (_, result_row) in enumerate(
    top10.iterrows()
):

    ax = axes[
        graph_index
    ]


    driver = (
        result_row[
            "Driver"
        ]
    )


    position = int(
        result_row[
            "position"
        ]
    )


    dd = clean_laps[

        clean_laps["Driver"]
        .eq(
            driver
        )

    ]


    ds = summary[

        summary["Driver"]
        .eq(
            driver
        )

    ]


    if dd.empty:

        ax.set_title(
            f"P{position} — {driver}\nNo valid data"
        )

        ax.axis(
            "off"
        )

        continue


    for _, row in (
        ds.iterrows()
    ):

        stint_num = int(
            row[
                "Stint"
            ]
        )


        compound = (
            row[
                "Compound"
            ]
        )


        color = (
            compound_colors.get(
                compound,
                "black"
            )
        )


        linestyle = (

            line_styles[
                (
                    stint_num
                    -
                    1
                )
                %
                len(
                    line_styles
                )
            ]
        )


        stint_data = dd[

            dd["Stint"]
            .eq(
                stint_num
            )

        ].sort_values(
            "TyreAge"
        )


        ax.scatter(

            stint_data[
                "TyreAge"
            ],

            stint_data[
                "DeltaToBest"
            ],

            color=color,

            s=35,

            alpha=0.75
        )


        # regression
        if (
            pd.notna(
                row[
                    "DegSlope"
                ]
            )

            and

            len(
                stint_data
            )
            >= 4
        ):

            x_fit = np.linspace(

                stint_data[
                    "TyreAge"
                ].min(),

                stint_data[
                    "TyreAge"
                ].max(),

                60
            )


            slope, intercept = (
                np.polyfit(

                    stint_data[
                        "TyreAge"
                    ],

                    stint_data[
                        "DeltaToBest"
                    ],

                    1
                )
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

                linestyle=linestyle,

                linewidth=2.2,

                label=(

                    f"S{stint_num} "
                    f"{compound} | "
                    f"{row['DegSlope']:+.3f}s/lap"

                )
            )


        else:

            ax.plot(

                stint_data[
                    "TyreAge"
                ],

                stint_data[
                    "DeltaToBest"
                ],

                color=color,

                linestyle=linestyle,

                linewidth=1.5,

                label=(

                    f"S{stint_num} "
                    f"{compound}"

                )
            )


    ax.axhline(
        0,
        linewidth=0.9,
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
        linestyle="--",
        alpha=0.20
    )


    ax.legend(
        fontsize=8
    )


fig.suptitle(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 TYRE DEGRADATION BY STINT\n"
    "Positive slope = lap time increases as tyre ages",

    fontsize=18,

    fontweight="bold",

    y=1.005
)


plt.tight_layout()

plt.show()


# ================================================================
# GRAPH 2
# AVERAGE PACE PER STINT
# ================================================================

plot_summary = (
    summary.copy()
)


plot_summary[
    "Label"
] = (

    "P"

    +

    plot_summary[
        "Position"
    ]
    .astype(int)
    .astype(str)

    +

    " "

    +

    plot_summary[
        "Driver"
    ]

    +

    " | Stint "

    +

    plot_summary[
        "Stint"
    ]
    .astype(int)
    .astype(str)

    +

    " | "

    +

    plot_summary[
        "Compound"
    ]

)


plot_summary = (
    plot_summary
    .iloc[::-1]
)


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


fig_height = max(

    10,

    len(
        plot_summary
    )
    *
    0.45

)


fig, ax = plt.subplots(

    figsize=(
        16,
        fig_height
    )

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


min_pace = (
    plot_summary[
        "AveragePace"
    ]
    .min()
)


max_pace = (
    plot_summary[
        "AveragePace"
    ]
    .max()
)


ax.set_xlim(

    min_pace - 1,

    max_pace + 2.5
)


for bar, (_, row) in zip(

    bars,

    plot_summary.iterrows()

):

    if pd.notna(
        row[
            "DegSlope"
        ]
    ):

        deg_text = (
            f"{row['DegSlope']:+.3f}s/lap"
        )

    else:

        deg_text = "-"


    ax.text(

        row[
            "AveragePace"
        ]
        +
        0.07,

        bar.get_y()
        +
        bar.get_height() / 2,

        (
            f"{format_laptime(row['AveragePace'])}"
            f" | deg {deg_text}"
        ),

        va="center",

        fontsize=8,

        fontweight="bold"
    )


ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 AVERAGE RACE PACE PER STINT\n"
    "Lower = Faster",

    fontsize=16,

    fontweight="bold",

    pad=18
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
# GRAPH 3
# DEGRADATION SLOPE RANKING
# ================================================================

deg_ranking = summary[

    summary["DegSlope"]
    .notna()

].copy()


deg_ranking = (
    deg_ranking
    .sort_values(
        "DegSlope"
    )
)


deg_ranking["Label"] = (

    deg_ranking["Driver"]

    +

    " S"

    +

    deg_ranking[
        "Stint"
    ]
    .astype(int)
    .astype(str)

    +

    " "

    +

    deg_ranking[
        "Compound"
    ]
)


plot_deg = (
    deg_ranking
    .iloc[::-1]
)


fig, ax = plt.subplots(

    figsize=(
        14,
        max(
            8,
            len(plot_deg)
            *
            0.40
        )
    )

)


colors = [

    compound_colors.get(
        c,
        "black"
    )

    for c in plot_deg[
        "Compound"
    ]

]


bars = ax.barh(

    plot_deg[
        "Label"
    ],

    plot_deg[
        "DegSlope"
    ],

    color=colors
)


ax.axvline(
    0,
    color="black",
    linewidth=1
)


for bar, (_, row) in zip(

    bars,

    plot_deg.iterrows()

):

    value = (
        row[
            "DegSlope"
        ]
    )


    ax.text(

        value
        +
        (
            0.005
            if value >= 0
            else -0.005
        ),

        bar.get_y()
        +
        bar.get_height()
        /
        2,

        f"{value:+.3f}s/lap",

        va="center",

        ha=(
            "left"
            if value >= 0
            else
            "right"
        ),

        fontsize=8,

        fontweight="bold"
    )


ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TYRE DEGRADATION SLOPE RANKING",

    fontsize=15,

    fontweight="bold"
)


ax.set_xlabel(
    "Observed Degradation (seconds / lap)"
)


ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


plt.tight_layout()

plt.show()


# ================================================================
# FINAL DEGRADATION TABLE
# ================================================================

deg_table = (
    deg_ranking.copy()
)


deg_table[
    "Average Pace"
] = (

    deg_table[
        "AveragePace"
    ]

    .apply(
        format_laptime
    )
)


deg_table[
    "Deg / Lap"
] = (

    deg_table[
        "DegSlope"
    ]

    .apply(
        lambda x:
        f"{x:+.3f} s/lap"
    )
)


print()
print(
    "=" * 105
)

print(
    "DEGRADATION RANKING — LOWEST TO HIGHEST"
)

print(
    "=" * 105
)


display(

    deg_table[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "ValidLaps",
            "Average Pace",
            "Deg / Lap"
        ]
    ]

)


print()
print(
    "NOTE:"
)

print(
    "DegSlope adalah observed degradation proxy, "
    "bukan pure tyre degradation."
)

print(
    "Fuel burn, traffic, track evolution, SC/VSC "
    "dan driver management tetap memengaruhi slope."
)
