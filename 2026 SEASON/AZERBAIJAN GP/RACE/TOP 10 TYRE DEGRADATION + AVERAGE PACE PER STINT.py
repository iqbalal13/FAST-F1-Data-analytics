# ================================================================
# AZERBAIJAN GP 2026 — BAKU
# TOP 10 TYRE DEGRADATION + AVERAGE PACE PER STINT
# OPENF1
# GOOGLE COLAB — ONE CELL
#
# FIX:
# - Tidak memakai endpoint PIT
# - Rate-limit safe
# - Retry otomatis HTTP 429
# - Pit-in ditentukan dari akhir stint
# - Pit-out dibuang dari is_pit_out_lap
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

# Dari notebook kamu:
# Azerbaijan GP 2026 Race = session_key 11377
SESSION_KEY = 11377

BASE = "https://api.openf1.org/v1"


# ================================================================
# RATE LIMIT SETTINGS
#
# Sengaja dibuat konservatif.
# ================================================================

LAST_REQUEST_TIME = 0

# sekitar 1 request / detik
MIN_REQUEST_INTERVAL = 1.05


# ================================================================
# HTTP SESSION
# ================================================================

http = requests.Session()

http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})


# ================================================================
# SAFE API GET
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

        # --------------------------------------------------------
        # THROTTLE
        # --------------------------------------------------------

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


        # --------------------------------------------------------
        # REQUEST
        # --------------------------------------------------------

        try:

            response = http.get(
                url,
                params=params,
                timeout=90
            )

            LAST_REQUEST_TIME = (
                time.time()
            )


        except requests.RequestException as e:

            wait = min(
                3 + (attempt * 2),
                20
            )

            print()
            print(
                f"Network error [{endpoint}]"
            )

            print(
                str(e)
            )

            print(
                f"Retry dalam {wait}s..."
            )

            time.sleep(wait)

            continue


        # --------------------------------------------------------
        # HTTP 429
        # --------------------------------------------------------

        if response.status_code == 429:

            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )


            if retry_after:

                try:

                    wait = float(
                        retry_after
                    )

                except:

                    wait = 3 + (
                        attempt * 2
                    )

            else:

                # jangan retry terlalu agresif
                wait = min(
                    3 + (
                        attempt * 3
                    ),
                    30
                )


            wait += random.uniform(
                0.3,
                1.0
            )


            print()
            print(
                "⚠️ OpenF1 rate limit 429"
            )

            print(
                "Endpoint:",
                endpoint
            )

            print(
                f"Retry "
                f"{attempt + 1}/"
                f"{max_retries} "
                f"dalam "
                f"{wait:.1f}s..."
            )


            time.sleep(
                wait
            )

            continue


        # --------------------------------------------------------
        # OTHER ERROR
        # --------------------------------------------------------

        if response.status_code != 200:

            print()
            print(
                "OPENF1 API ERROR"
            )

            print(
                "URL:",
                response.url
            )

            print(
                "Status:",
                response.status_code
            )

            print(
                "Body:",
                response.text[:500]
            )

            raise RuntimeError(
                f"OpenF1 HTTP "
                f"{response.status_code}"
            )


        # --------------------------------------------------------
        # SUCCESS
        # --------------------------------------------------------

        data = response.json()


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
        f"OpenF1 gagal setelah "
        f"{max_retries} retry "
        f"untuk endpoint "
        f"{endpoint}"
    )


# ================================================================
# LAP TIME FORMAT
# ================================================================

def format_laptime(seconds):

    if pd.isna(seconds):

        return "-"


    minutes = int(
        seconds // 60
    )


    sec = (
        seconds
        %
        60
    )


    return (
        f"{minutes}:"
        f"{sec:06.3f}"
    )


# ================================================================
# 1. DRIVER DATA
# ================================================================

print(
    "=" * 80
)

print(
    "AZERBAIJAN GP 2026 — TYRE DEGRADATION ANALYSIS"
)

print(
    "=" * 80
)

print(
    "Session Key:",
    SESSION_KEY
)


print(
    "\n[1/4] Loading drivers..."
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


drivers[
    "driver_number"
] = pd.to_numeric(
    drivers[
        "driver_number"
    ],
    errors="coerce"
)


drivers = drivers.dropna(
    subset=[
        "driver_number"
    ]
)


drivers[
    "driver_number"
] = (
    drivers[
        "driver_number"
    ]
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

    [
        "name_acronym"
    ]

    .to_dict()

)


# ================================================================
# 2. TOP 10 FINAL RESULT
# ================================================================

print(
    "[2/4] Loading race result..."
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


results[
    "position"
] = pd.to_numeric(
    results[
        "position"
    ],
    errors="coerce"
)


results[
    "driver_number"
] = pd.to_numeric(
    results[
        "driver_number"
    ],
    errors="coerce"
)


top10 = results[

    results[
        "position"
    ].between(
        1,
        10
    )

].copy()


top10 = (
    top10
    .sort_values(
        "position"
    )
)


top10[
    "driver_number"
] = (
    top10[
        "driver_number"
    ]
    .astype(int)
)


top10[
    "Driver"
] = (

    top10[
        "driver_number"
    ]

    .map(
        driver_map
    )

)


top10[
    "Driver"
] = (
    top10[
        "Driver"
    ]

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


print()
print(
    "=" * 80
)

print(
    "TOP 10 FINISHERS"
)

print(
    "=" * 80
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
# 3. LOAD LAPS
# ================================================================

print(
    "\n[3/4] Loading race laps..."
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

        laps[
            col
        ] = pd.to_numeric(
            laps[
                col
            ],
            errors="coerce"
        )


laps = laps[

    laps[
        "driver_number"
    ].isin(
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
    laps[
        "lap_duration"
    ] > 0
].copy()


print(
    "Top 10 lap records:",
    len(laps)
)


# ================================================================
# 4. LOAD STINTS
# ================================================================

print(
    "[4/4] Loading tyre stints..."
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


# ------------------------------------------------
# safe numeric conversion
# ------------------------------------------------

numeric_stint_columns = [
    "driver_number",
    "stint_number",
    "lap_start",
    "lap_end",
    "tyre_age_at_start"
]


for col in numeric_stint_columns:

    if col in stints.columns:

        stints[
            col
        ] = pd.to_numeric(
            stints[
                col
            ],
            errors="coerce"
        )


# tyre age fallback
if (
    "tyre_age_at_start"
    not in stints.columns
):

    stints[
        "tyre_age_at_start"
    ] = 0


stints[
    "tyre_age_at_start"
] = (

    stints[
        "tyre_age_at_start"
    ]

    .fillna(0)

)


# compound fallback
if (
    "compound"
    not in stints.columns
):

    stints[
        "compound"
    ] = "UNKNOWN"


stints = stints[

    stints[
        "driver_number"
    ].isin(
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
    "Top 10 stints:",
    len(stints)
)


# ================================================================
# COMPOUND COLORS
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
# PROCESS STINTS
# ================================================================

clean_lap_frames = []

summary_rows = []


for _, result_row in (
    top10.iterrows()
):

    # ------------------------------------------------------------
    # DRIVER
    # ------------------------------------------------------------

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


    # ------------------------------------------------------------
    # ALL STINTS DRIVER
    # ------------------------------------------------------------

    driver_stints = stints[

        stints[
            "driver_number"
        ]
        ==
        driver_num

    ].copy()


    driver_stints = (
        driver_stints
        .sort_values(
            "stint_number"
        )
        .reset_index(
            drop=True
        )
    )


    if driver_stints.empty:

        continue


    # jumlah stint
    number_of_stints = (
        len(
            driver_stints
        )
    )


    # ------------------------------------------------------------
    # PROCESS EACH STINT
    # ------------------------------------------------------------

    for stint_idx, stint in (
        driver_stints.iterrows()
    ):

        if (
            pd.isna(
                stint[
                    "lap_start"
                ]
            )

            or

            pd.isna(
                stint[
                    "lap_end"
                ]
            )
        ):

            continue


        # ========================================================
        # STINT NUMBER
        # ========================================================

        if (
            pd.notna(
                stint.get(
                    "stint_number",
                    np.nan
                )
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


        # ========================================================
        # LAP RANGE
        # ========================================================

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


        # ========================================================
        # COMPOUND
        # ========================================================

        compound = str(
            stint.get(
                "compound",
                "UNKNOWN"
            )
        ).upper()


        if compound in [
            "NAN",
            "NONE",
            ""
        ]:

            compound = (
                "UNKNOWN"
            )


        # ========================================================
        # TYRE AGE START
        # ========================================================

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


        # ========================================================
        # GET LAPS FOR STINT
        # ========================================================

        stint_laps = laps[

            (
                laps[
                    "driver_number"
                ]
                ==
                driver_num
            )

            &

            (
                laps[
                    "lap_number"
                ]
                >=
                lap_start
            )

            &

            (
                laps[
                    "lap_number"
                ]
                <=
                lap_end
            )

        ].copy()


        # ========================================================
        # VALID LAP DATA
        # ========================================================

        stint_laps = (
            stint_laps
            .dropna(
                subset=[
                    "lap_number",
                    "lap_duration"
                ]
            )
        )


        stint_laps = stint_laps[

            stint_laps[
                "lap_duration"
            ]
            >
            0

        ].copy()


        # ========================================================
        # REMOVE LAP 1
        #
        # Standing-start lap.
        # ========================================================

        stint_laps = stint_laps[

            stint_laps[
                "lap_number"
            ]
            >
            1

        ].copy()


        # ========================================================
        # REMOVE PIT-OUT
        # ========================================================

        if (
            "is_pit_out_lap"
            in
            stint_laps.columns
        ):

            stint_laps = stint_laps[

                stint_laps[
                    "is_pit_out_lap"
                ]
                !=
                True

            ].copy()


        # ========================================================
        # REMOVE PIT-IN LAP
        #
        # Tidak perlu endpoint PIT.
        #
        # Untuk semua stint kecuali stint terakhir:
        # lap_end = lap masuk pit.
        # ========================================================

        is_final_stint = (

            stint_idx

            ==
            (
                number_of_stints
                -
                1
            )

        )


        if not is_final_stint:

            stint_laps = stint_laps[

                stint_laps[
                    "lap_number"
                ]
                !=
                lap_end

            ].copy()


        # ========================================================
        # MINIMUM DATA
        # ========================================================

        if len(
            stint_laps
        ) < 2:

            continue


        # ========================================================
        # TYRE AGE
        # ========================================================

        stint_laps[
            "TyreAge"
        ] = (

            tyre_age_start

            +

            (
                stint_laps[
                    "lap_number"
                ]
                -
                lap_start
            )

        )


        # ========================================================
        # ROBUST OUTLIER REMOVAL
        #
        # MAD:
        # Median Absolute Deviation
        #
        # Removes extreme:
        # - Safety Car laps
        # - yellow laps
        # - mistakes
        # - severe traffic
        # ========================================================

        median_laptime = (

            stint_laps[
                "lap_duration"
            ]
            .median()

        )


        absolute_deviation = np.abs(

            stint_laps[
                "lap_duration"
            ]

            -

            median_laptime

        )


        mad = np.median(
            absolute_deviation
        )


        robust_sigma = (
            1.4826
            *
            mad
        )


        # minimum tolerance
        threshold = max(

            3.5
            *
            robust_sigma,

            2.5

        )


        clean = stint_laps[

            np.abs(

                stint_laps[
                    "lap_duration"
                ]

                -

                median_laptime

            )

            <=
            threshold

        ].copy()


        # ========================================================
        # MIN DATA AFTER CLEANING
        # ========================================================

        if len(clean) < 2:

            continue


        # ========================================================
        # STINT STATISTICS
        # ========================================================

        average_pace = (

            clean[
                "lap_duration"
            ]
            .mean()

        )


        median_pace = (

            clean[
                "lap_duration"
            ]
            .median()

        )


        best_lap = (

            clean[
                "lap_duration"
            ]
            .min()

        )


        # ========================================================
        # DELTA TO STINT BEST
        # ========================================================

        clean[
            "DeltaToBest"
        ] = (

            clean[
                "lap_duration"
            ]

            -

            best_lap

        )


        # ========================================================
        # DEGRADATION SLOPE
        #
        # seconds per lap
        # ========================================================

        deg_slope = np.nan


        if (
            len(clean)
            >=
            4

            and

            clean[
                "TyreAge"
            ].nunique()
            >=
            4
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


        # ========================================================
        # SAVE CLEAN LAPS
        # ========================================================

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


        clean_lap_frames.append(
            clean
        )


        # ========================================================
        # SUMMARY ROW
        # ========================================================

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
# CREATE DATAFRAMES
# ================================================================

if not clean_lap_frames:

    raise RuntimeError(
        "Tidak ada valid clean stint data."
    )


clean_laps = pd.concat(
    clean_lap_frames,
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
# DISPLAY SUMMARY TABLE
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
    "=" * 100
)

print(
    "TOP 10 — TYRE DEGRADATION & AVERAGE STINT PACE"
)

print(
    "=" * 100
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
            "ValidLaps",
            "Average Pace",
            "Median Pace",
            "Best Lap",
            "Deg / Lap"
        ]
    ]

)


# ================================================================
# 1ST GRAPH
# TYRE DEGRADATION PER DRIVER
# ================================================================

fig, axes = plt.subplots(

    5,
    2,

    figsize=(
        17,
        24
    )

)


axes = (
    axes.flatten()
)


for plot_index, (
    _,
    result_row
) in enumerate(
    top10.iterrows()
):

    ax = axes[
        plot_index
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


    driver_data = clean_laps[

        clean_laps[
            "Driver"
        ]
        ==
        driver

    ]


    driver_summary = summary[

        summary[
            "Driver"
        ]
        ==
        driver

    ]


    if driver_data.empty:

        ax.set_title(
            f"P{position} — {driver}\nNo data"
        )

        ax.axis(
            "off"
        )

        continue


    # ------------------------------------------------------------
    # STINTS DRIVER
    # ------------------------------------------------------------

    for _, stint_row in (
        driver_summary.iterrows()
    ):

        stint_num = int(
            stint_row[
                "Stint"
            ]
        )


        compound = (
            stint_row[
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


        stint_data = driver_data[

            driver_data[
                "Stint"
            ]
            ==
            stint_num

        ].sort_values(
            "TyreAge"
        )


        # ========================================================
        # POINTS
        # ========================================================

        ax.scatter(

            stint_data[
                "TyreAge"
            ],

            stint_data[
                "DeltaToBest"
            ],

            color=color,

            s=32,

            alpha=0.75

        )


        # ========================================================
        # TREND LINE
        # ========================================================

        if (
            pd.notna(
                stint_row[
                    "DegSlope"
                ]
            )

            and

            len(
                stint_data
            )
            >=
            4
        ):

            x_fit = np.linspace(

                stint_data[
                    "TyreAge"
                ].min(),

                stint_data[
                    "TyreAge"
                ].max(),

                50

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

                linewidth=2,

                label=(

                    f"S{stint_num} "
                    f"{compound} "
                    f"{stint_row['DegSlope']:+.3f}s/lap"

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


    # ============================================================
    # DRIVER GRAPH STYLE
    # ============================================================

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
        "Delta to Stint Best (s)"
    )


    ax.grid(
        alpha=0.2,
        linestyle="--"
    )


    ax.legend(
        fontsize=8
    )


fig.suptitle(

    "AZERBAIJAN GP 2026 — TOP 10 TYRE DEGRADATION\n"
    "Positive slope = lap time tends to increase as tyre ages",

    fontsize=18,

    fontweight="bold",

    y=1.005

)


plt.tight_layout()

plt.show()


# ================================================================
# 2ND GRAPH
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

    " | S"

    +

    plot_summary[
        "Stint"
    ]
    .astype(int)
    .astype(str)

    +

    " "

    +

    plot_summary[
        "Compound"
    ]

)


# reverse so P1 appears nearer top

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


fig, ax = plt.subplots(
    figsize=(
        15,
        12
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


# ================================================================
# ZOOM X-AXIS
# ================================================================

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

    min_pace
    -
    1.0,

    max_pace
    +
    2.0

)


# ================================================================
# LABELS
# ================================================================

for bar, (_, row) in zip(

    bars,

    plot_summary.iterrows()

):

    pace_text = (
        format_laptime(
            row[
                "AveragePace"
            ]
        )
    )


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
        0.05,

        bar.get_y()
        +
        (
            bar.get_height()
            /
            2
        ),

        (
            f"{pace_text}"
            f" | deg {deg_text}"
        ),

        va="center",

        fontsize=8,

        fontweight="bold"

    )


ax.set_title(

    "AZERBAIJAN GP 2026 — AVERAGE PACE PER STINT\n"
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
# DEGRADATION RANKING
# ================================================================

deg_ranking = summary[

    summary[
        "DegSlope"
    ]
    .notna()

].copy()


deg_ranking = (

    deg_ranking
    .sort_values(
        "DegSlope"
    )

)


print()
print(
    "=" * 100
)

print(
    "TYRE DEGRADATION RANKING — LOWEST TO HIGHEST"
)

print(
    "=" * 100
)


deg_table = (

    deg_ranking[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "ValidLaps",
            "AveragePace",
            "DegSlope"
        ]
    ]

    .copy()

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

    .map(
        lambda x:
        f"{x:+.3f} s/lap"
    )

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
