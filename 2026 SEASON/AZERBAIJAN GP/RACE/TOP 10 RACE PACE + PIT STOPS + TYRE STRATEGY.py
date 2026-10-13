# ================================================================
# AZERBAIJAN GP 2026 — BAKU
# TOP 10 RACE PACE + PIT STOPS + TYRE STRATEGY
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

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from matplotlib.lines import Line2D


# ================================================================
# CONFIG
# ================================================================

YEAR = 2026
BASE = "https://api.openf1.org/v1"

# Sengaja lebih lambat dari batas 3 req/sec
MIN_REQUEST_INTERVAL = 0.60
LAST_REQUEST_TIME = 0


# ================================================================
# HTTP SESSION
# ================================================================

http = requests.Session()

retry_strategy = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

http.mount(
    "https://",
    HTTPAdapter(max_retries=retry_strategy)
)

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

        # --------------------------------------------------------
        # THROTTLE
        # --------------------------------------------------------

        elapsed = time.time() - LAST_REQUEST_TIME

        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(
                MIN_REQUEST_INTERVAL - elapsed
            )

        # --------------------------------------------------------
        # REQUEST
        # --------------------------------------------------------

        try:

            r = http.get(
                url,
                params=params,
                timeout=90
            )

            LAST_REQUEST_TIME = time.time()

        except requests.RequestException as e:

            wait = min(
                2 ** attempt,
                20
            )

            print(
                f"\nNetwork error pada {endpoint}: {e}"
            )

            print(
                f"Retry dalam {wait}s..."
            )

            time.sleep(wait)
            continue


        # --------------------------------------------------------
        # RATE LIMIT 429
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
                        2 ** attempt,
                        30
                    )

            else:

                # exponential backoff
                wait = min(
                    2 ** attempt,
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
                f"Retry {attempt + 1}/{max_retries} "
                f"dalam {wait:.1f}s..."
            )

            time.sleep(wait)
            continue


        # --------------------------------------------------------
        # OTHER HTTP ERROR
        # --------------------------------------------------------

        if r.status_code != 200:

            print()
            print("API ERROR")
            print("URL    :", r.url)
            print("Status :", r.status_code)
            print("Body   :", r.text[:500])

            raise RuntimeError(
                f"OpenF1 HTTP {r.status_code}"
            )


        # --------------------------------------------------------
        # SUCCESS
        # --------------------------------------------------------

        data = r.json()

        if not data and not allow_empty:

            raise RuntimeError(
                f"Tidak ada data dari endpoint {endpoint}"
            )

        return data


    raise RuntimeError(
        f"OpenF1 gagal setelah {max_retries} retry "
        f"pada endpoint {endpoint}"
    )


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
# LAP TIME FORMAT
# ================================================================

def format_laptime(seconds):

    if pd.isna(seconds):
        return "-"

    minutes = int(
        seconds // 60
    )

    sec = (
        seconds % 60
    )

    return (
        f"{minutes}:{sec:06.3f}"
    )


# ================================================================
# 1. FIND BAKU RACE SESSION
# ================================================================

print(
    "=" * 75
)

print(
    "SEARCHING AZERBAIJAN / BAKU 2026 RACE"
)

print(
    "=" * 75
)


sessions = pd.DataFrame(
    api_get(
        "sessions",
        {
            "year": YEAR
        }
    )
)


# Safe columns

location_series = (
    sessions["location"]
    if "location" in sessions.columns
    else pd.Series(
        "",
        index=sessions.index
    )
)


circuit_series = (
    sessions["circuit_short_name"]
    if "circuit_short_name" in sessions.columns
    else pd.Series(
        "",
        index=sessions.index
    )
)


country_series = (
    sessions["country_name"]
    if "country_name" in sessions.columns
    else pd.Series(
        "",
        index=sessions.index
    )
)


baku_mask = (

    location_series
    .astype(str)
    .str.contains(
        "Baku",
        case=False,
        na=False
    )

    |

    circuit_series
    .astype(str)
    .str.contains(
        "Baku",
        case=False,
        na=False
    )

    |

    country_series
    .astype(str)
    .str.contains(
        "Azerbaijan",
        case=False,
        na=False
    )
)


baku_sessions = sessions[
    baku_mask
].copy()


race_sessions = baku_sessions[

    baku_sessions[
        "session_name"
    ]
    .astype(str)
    .str.lower()
    .eq("race")

].copy()


if race_sessions.empty:

    raise RuntimeError(
        "Azerbaijan / Baku race 2026 "
        "tidak ditemukan."
    )


race_sessions[
    "parsed_start"
] = parse_dt(
    race_sessions[
        "date_start"
    ]
)


race_sessions = (
    race_sessions
    .sort_values(
        "parsed_start"
    )
)


race_session = (
    race_sessions
    .iloc[-1]
)


SESSION_KEY = int(
    race_session[
        "session_key"
    ]
)


print(
    "Session :",
    race_session[
        "session_name"
    ]
)

print(
    "Location:",
    race_session[
        "location"
    ]
)

print(
    "Circuit :",
    race_session[
        "circuit_short_name"
    ]
)

print(
    "Key     :",
    SESSION_KEY
)


# ================================================================
# 2. DRIVER DATA
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
    )[
        "name_acronym"
    ]
    .to_dict()

)


# ================================================================
# 3. TOP 10 FINAL RESULT
# ================================================================

print(
    "Loading official result..."
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


top10 = top10.sort_values(
    "position"
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


TOP10_NUMBERS = (
    top10[
        "driver_number"
    ]
    .tolist()
)


print()
print(
    "=" * 75
)

print(
    "TOP 10 FINISHERS"
)

print(
    "=" * 75
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
# 4. LOAD RACE LAPS
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
    ]
    .isin(
        TOP10_NUMBERS
    )

].copy()


laps = laps.dropna(
    subset=[
        "driver_number",
        "lap_number",
        "lap_duration"
    ]
)


print(
    "Top 10 lap records:",
    len(laps)
)


# ================================================================
# 5. LOAD PIT STOPS
# ================================================================

print(
    "Loading pit stops..."
)


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

    for col in [
        "driver_number",
        "lap_number",
        "stop_duration",
        "lane_duration"
    ]:

        if col in pit.columns:

            pit[
                col
            ] = pd.to_numeric(
                pit[
                    col
                ],
                errors="coerce"
            )


    pit = pit[

        pit[
            "driver_number"
        ]
        .isin(
            TOP10_NUMBERS
        )

    ].copy()


    # stationary stop duration
    if "stop_duration" in pit.columns:

        pit[
            "StopTime"
        ] = pit[
            "stop_duration"
        ]

    else:

        pit[
            "StopTime"
        ] = np.nan


else:

    pit = pd.DataFrame(
        columns=[
            "driver_number",
            "lap_number",
            "stop_duration",
            "lane_duration",
            "StopTime"
        ]
    )


print(
    "Top 10 pit stops:",
    len(pit)
)


# ================================================================
# 6. LOAD STINTS
# ================================================================

print(
    "Loading tyre stints..."
)


stint_data = api_get(
    "stints",
    {
        "session_key":
            SESSION_KEY
    },
    allow_empty=True
)


stints = pd.DataFrame(
    stint_data
)


if not stints.empty:

    for col in [
        "driver_number",
        "stint_number",
        "lap_start",
        "lap_end"
    ]:

        if col in stints.columns:

            stints[
                col
            ] = pd.to_numeric(
                stints[
                    col
                ],
                errors="coerce"
            )


    stints = stints[

        stints[
            "driver_number"
        ]
        .isin(
            TOP10_NUMBERS
        )

    ].copy()


print(
    "Top 10 stints:",
    len(stints)
)


# ================================================================
# 7. CLEAN RACE PACE
# ================================================================

pace_frames = []


for _, result_row in (
    top10.iterrows()
):

    driver_num = int(
        result_row[
            "driver_number"
        ]
    )


    d = laps[

        laps[
            "driver_number"
        ]
        ==
        driver_num

    ].copy()


    # --------------------------------
    # valid lap
    # --------------------------------

    d = d.dropna(
        subset=[
            "lap_number",
            "lap_duration"
        ]
    )


    d = d[
        d[
            "lap_duration"
        ] > 0
    ]


    # --------------------------------
    # remove lap 1
    # standing-start lap
    # --------------------------------

    d = d[
        d[
            "lap_number"
        ] > 1
    ]


    # --------------------------------
    # remove pit-out
    # --------------------------------

    if (
        "is_pit_out_lap"
        in
        d.columns
    ):

        d = d[
            d[
                "is_pit_out_lap"
            ] != True
        ]


    # --------------------------------
    # remove pit-in lap
    # --------------------------------

    if not pit.empty:

        dp = pit[

            pit[
                "driver_number"
            ]
            ==
            driver_num

        ]


        pit_laps = (

            dp[
                "lap_number"
            ]
            .dropna()
            .astype(int)
            .tolist()

        )


        if pit_laps:

            d = d[

                ~d[
                    "lap_number"
                ]
                .astype(int)
                .isin(
                    pit_laps
                )

            ]


    if d.empty:
        continue


    # --------------------------------
    # Remove extreme slow laps
    # --------------------------------

    median_time = (
        d[
            "lap_duration"
        ]
        .median()
    )


    # +8 sec threshold
    d = d[

        d[
            "lap_duration"
        ]
        <=
        (
            median_time
            +
            8.0
        )

    ].copy()


    if d.empty:
        continue


    # --------------------------------
    # rolling median
    # --------------------------------

    d = d.sort_values(
        "lap_number"
    )


    d[
        "RacePace"
    ] = (

        d[
            "lap_duration"
        ]
        .rolling(
            window=3,
            center=True,
            min_periods=1
        )
        .median()

    )


    d[
        "Driver"
    ] = result_row[
        "Driver"
    ]


    d[
        "Position"
    ] = int(
        result_row[
            "position"
        ]
    )


    pace_frames.append(
        d
    )


if not pace_frames:

    raise RuntimeError(
        "Tidak ada valid race pace data."
    )


pace = pd.concat(
    pace_frames,
    ignore_index=True
)


# ================================================================
# 8. RACE PACE SUMMARY
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


# ================================================================
# PIT COUNT
# ================================================================

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


    pace_summary[
        "PitStops"
    ] = (

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

    pace_summary[
        "PitStops"
    ] = 0


# ================================================================
# DISPLAY SUMMARY
# ================================================================

print()
print(
    "=" * 75
)

print(
    "RACE PACE SUMMARY"
)

print(
    "=" * 75
)


summary_display = (
    pace_summary.copy()
)


summary_display[
    "Median Pace"
] = (

    summary_display[
        "MedianPace"
    ]
    .apply(
        format_laptime
    )

)


summary_display[
    "Mean Pace"
] = (

    summary_display[
        "MeanPace"
    ]
    .apply(
        format_laptime
    )

)


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
# 9. FIGURE
# ================================================================

fig, (
    ax1,
    ax2
) = plt.subplots(

    2,
    1,

    figsize=(
        16,
        12
    ),

    gridspec_kw={
        "height_ratios":
            [
                2.3,
                1.2
            ]
    },

    sharex=True
)


# ================================================================
# DRIVER COLORS
# ================================================================

cmap = plt.colormaps[
    "tab10"
]


driver_colors = {

    int(
        row[
            "driver_number"
        ]
    ):
        cmap(i)

    for i, (_, row)
    in enumerate(
        top10.iterrows()
    )

}


# ================================================================
# 10. TOP GRAPH — RACE PACE
# ================================================================

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


    position = int(
        result_row[
            "position"
        ]
    )


    d = pace[

        pace[
            "driver_number"
        ]
        ==
        driver_num

    ].copy()


    if d.empty:
        continue


    color = (
        driver_colors[
            driver_num
        ]
    )


    ax1.plot(

        d[
            "lap_number"
        ],

        d[
            "RacePace"
        ],

        linewidth=2,

        color=color,

        label=
            f"P{position} {driver}"

    )


    # ============================================================
    # PIT MARKER
    # ============================================================

    if not pit.empty:

        dp = pit[

            pit[
                "driver_number"
            ]
            ==
            driver_num

        ]


        for _, stop in (
            dp.iterrows()
        ):

            if pd.isna(
                stop[
                    "lap_number"
                ]
            ):
                continue


            pit_lap = int(
                stop[
                    "lap_number"
                ]
            )


            # nearest remaining pace lap
            nearest_idx = (

                d[
                    "lap_number"
                ]

                .sub(
                    pit_lap
                )

                .abs()

                .idxmin()

            )


            pit_y = (
                d.loc[
                    nearest_idx,
                    "RacePace"
                ]
            )


            ax1.scatter(

                pit_lap,
                pit_y,

                marker="v",

                s=85,

                color=color,

                edgecolor="black",

                linewidth=0.7,

                zorder=10

            )


# ================================================================
# TOP GRAPH STYLE
# ================================================================

ax1.set_title(

    "AZERBAIJAN GP 2026 — TOP 10 RACE PACE + PIT STOPS\n"
    "3-Lap Rolling Median | Lower = Faster",

    fontsize=16,

    fontweight="bold",

    pad=18
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
# 11. BOTTOM — TYRE STINT / PIT STRATEGY
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


        for _, stint in (
            ds.iterrows()
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


            if (
                compound == "NAN"
                or
                compound == "NONE"
            ):

                compound = "UNKNOWN"


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

                linewidth=13,

                color=tyre_color,

                alpha=0.85
            )


            # compound abbreviation
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


    # ============================================================
    # STINT FALLBACK
    # ============================================================

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


        for _, stop in (
            dp.iterrows()
        ):

            if pd.isna(
                stop[
                    "lap_number"
                ]
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


            # stationary stop duration
            if (
                "StopTime"
                in
                stop.index
                and
                pd.notna(
                    stop[
                        "StopTime"
                    ]
                )
            ):

                ax2.text(

                    pit_lap,

                    y - 0.28,

                    f"{stop['StopTime']:.1f}s",

                    ha="center",

                    va="center",

                    fontsize=7,

                    fontweight="bold"

                )


# ================================================================
# BOTTOM GRAPH STYLE
# ================================================================

ax2.set_yticks(
    yticks
)


ax2.set_yticklabels(
    ylabels
)


# P1 at top
ax2.invert_yaxis()


ax2.set_xlabel(
    "Race Lap"
)


ax2.set_ylabel(
    "Top 10 Finishers"
)


ax2.set_title(

    "Tyre Strategy & Pit Stops\n"
    "▼ = Pit Stop | S = Soft | M = Medium | H = Hard",

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
# COMPOUND LEGEND
# ================================================================

used_compounds = []


if (
    not stints.empty
    and
    "compound"
    in
    stints.columns
):

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


for compound in (
    used_compounds
):

    if compound in [
        "NAN",
        "NONE"
    ]:

        continue


    legend_elements.append(

        Line2D(

            [0],
            [0],

            color=
                compound_colors.get(
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

    handles=
        legend_elements,

    loc=
        "upper center",

    bbox_to_anchor=(
        0.5,
        -0.14
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
# 12. PIT STOP TABLE
# ================================================================

print()
print(
    "=" * 75
)

print(
    "TOP 10 PIT STOP DETAILS"
)

print(
    "=" * 75
)


if pit.empty:

    print(
        "Tidak ada pit-stop data."
    )


else:

    pit_table = (
        pit.copy()
    )


    pit_table[
        "Driver"
    ] = (

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
        )[
            "position"
        ]

        .to_dict()

    )


    pit_table[
        "Position"
    ] = (

        pit_table[
            "driver_number"
        ]

        .map(
            position_map
        )

    )


    pit_table = (
        pit_table
        .sort_values(
            [
                "Position",
                "lap_number"
            ]
        )
    )


    # only use columns that actually exist
    wanted_columns = [
        "Position",
        "Driver",
        "lap_number",
        "StopTime",
        "lane_duration"
    ]


    existing_columns = [

        col

        for col
        in wanted_columns

        if col
        in pit_table.columns

    ]


    pit_display = (
        pit_table[
            existing_columns
        ]
        .copy()
    )


    pit_display = (
        pit_display.rename(
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


    display(
        pit_display
    )
