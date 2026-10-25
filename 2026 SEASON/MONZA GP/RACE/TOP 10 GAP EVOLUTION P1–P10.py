# ================================================================
# ITALIAN GP 2026 — MONZA
# TOP 10 GAP EVOLUTION P1–P10
#
# Gap to Race Leader at End of Each Lap
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
# SAFE API
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
                3
                +
                attempt * 3,

                30
            )


            print(
                f"Network error [{endpoint}]: {e}"
            )


            print(
                f"Retry in {wait}s..."
            )


            time.sleep(
                wait
            )


            continue


        # ========================================================
        # 429
        # ========================================================

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
                        4
                        +
                        attempt * 4,

                        40
                    )


            else:

                wait = min(
                    4
                    +
                    attempt * 4,

                    40
                )


            wait += random.uniform(
                0.3,
                1.0
            )


            print()
            print(
                "⚠️ OpenF1 rate limit"
            )


            print(
                "Endpoint:",
                endpoint
            )


            print(
                f"Retry {attempt+1}/{max_retries} "
                f"in {wait:.1f}s..."
            )


            time.sleep(
                wait
            )


            continue


        # ========================================================
        # ERROR
        # ========================================================

        if r.status_code != 200:

            print()
            print(
                "API ERROR"
            )


            print(
                "URL:",
                r.url
            )


            print(
                "Status:",
                r.status_code
            )


            print(
                "Body:",
                r.text[:500]
            )


            raise RuntimeError(
                f"OpenF1 HTTP "
                f"{r.status_code}"
            )


        # ========================================================
        # SUCCESS
        # ========================================================

        data = (
            r.json()
        )


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
# FIND MONZA RACE
# ================================================================

print(
    "=" * 90
)

print(
    "ITALIAN GP 2026 — MONZA"
)

print(
    "TOP 10 GAP EVOLUTION"
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

    sessions[
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
        "Monza race tidak ditemukan."
    )


race_sessions[
    "_date"
] = parse_dt(
    race_sessions[
        "date_start"
    ]
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
# TOP 10 FINAL RESULT
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
    ]
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
        ]
        .astype(str)
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
# LOAD LAP DATA
# ================================================================

print(
    "\nLoading lap data..."
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

    laps[col] = pd.to_numeric(
        laps[col],
        errors="coerce"
    )


laps[
    "date_start_dt"
] = parse_dt(
    laps[
        "date_start"
    ]
)


laps = laps[

    laps[
        "driver_number"
    ]
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


# ================================================================
# CALCULATE LAP END
# ================================================================

laps[
    "lap_end_dt"
] = (

    laps[
        "date_start_dt"
    ]

    +

    pd.to_timedelta(
        laps[
            "lap_duration"
        ],
        unit="s"
    )

)


print(
    "Top-10 lap records:",
    len(laps)
)


# ================================================================
# INTERVAL DATA
# ================================================================

print(
    "Loading intervals..."
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


intervals[
    "driver_number"
] = pd.to_numeric(
    intervals[
        "driver_number"
    ],
    errors="coerce"
)


intervals[
    "date_dt"
] = parse_dt(
    intervals[
        "date"
    ]
)


intervals[
    "gap_raw"
] = (
    intervals[
        "gap_to_leader"
    ]
)


intervals[
    "gap_seconds"
] = pd.to_numeric(
    intervals[
        "gap_to_leader"
    ],
    errors="coerce"
)


intervals = intervals[

    intervals[
        "driver_number"
    ]
    .isin(
        TOP10
    )

].copy()


intervals = intervals.dropna(
    subset=[
        "driver_number",
        "date_dt"
    ]
)


# ================================================================
# CREATE LAP-BY-LAP GAP
# ================================================================

gap_frames = []


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


    driver_laps = laps[

        laps[
            "driver_number"
        ]
        ==
        driver_num

    ][
        [
            "lap_number",
            "lap_end_dt"
        ]
    ].copy()


    driver_intervals = intervals[

        intervals[
            "driver_number"
        ]
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


    driver_laps = (
        driver_laps
        .sort_values(
            "lap_end_dt"
        )
    )


    driver_intervals = (
        driver_intervals
        .sort_values(
            "date_dt"
        )
    )


    merged = pd.merge_asof(

        driver_laps,

        driver_intervals,

        left_on=
            "lap_end_dt",

        right_on=
            "date_dt",

        direction=
            "nearest",

        tolerance=
            pd.Timedelta(
                seconds=8
            )

    )


    # ============================================================
    # LEADER = 0
    # ============================================================

    leader_mask = (

        merged[
            "date_dt"
        ]
        .notna()

        &

        merged[
            "gap_raw"
        ]
        .isna()

    )


    merged.loc[

        leader_mask,

        "gap_seconds"

    ] = 0.0


    merged[
        "Driver"
    ] = driver


    merged[
        "FinishPosition"
    ] = finish_position


    merged[
        "driver_number"
    ] = driver_num


    gap_frames.append(
        merged
    )


if not gap_frames:

    raise RuntimeError(
        "Tidak berhasil membuat "
        "lap-by-lap gap evolution."
    )


gap_laps = pd.concat(
    gap_frames,
    ignore_index=True
)


# ================================================================
# TABLE SAMPLE
# ================================================================

print()
print(
    "=" * 90
)

print(
    "GAP TO LEADER — END OF EACH LAP"
)

print(
    "=" * 90
)


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
# DRIVER COLORS
# ================================================================

cmap = plt.colormaps[
    "tab10"
]


driver_colors = {

    row[
        "Driver"
    ]:
        cmap(i)

    for i, (_, row)
    in enumerate(
        top10.iterrows()
    )

}


# ================================================================
# GRAPH 1 — GAP EVOLUTION
# ================================================================

fig, ax = plt.subplots(
    figsize=(
        18,
        10
    )
)


for _, result_row in (
    top10.iterrows()
):

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


    d = gap_laps[

        gap_laps[
            "Driver"
        ]
        ==
        driver

    ].sort_values(
        "lap_number"
    )


    d = d[
        d[
            "gap_seconds"
        ]
        .notna()
    ]


    if d.empty:

        continue


    ax.plot(

        d[
            "lap_number"
        ],

        d[
            "gap_seconds"
        ],

        linewidth=2.3,

        marker="o",

        markersize=2.5,

        color=
            driver_colors[
                driver
            ],

        label=(
            f"P{position} {driver}"
        )

    )


# ================================================================
# STYLE
# ================================================================

ax.axhline(

    0,

    color="black",

    linewidth=1,

    alpha=0.5

)


ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 GAP EVOLUTION — P1 TO P10\n"
    "Gap to Race Leader at End of Each Lap",

    fontsize=18,

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

    fontsize=10,

    loc="upper left"

)


plt.tight_layout()

plt.show()


# ================================================================
# GRAPH 2 — GAP EVOLUTION NORMALIZED TO EACH DRIVER'S START
#
# Useful to see who gained/lost relative time through race.
# ================================================================

fig, ax = plt.subplots(
    figsize=(
        18,
        9
    )
)


for _, result_row in (
    top10.iterrows()
):

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


    d = gap_laps[

        gap_laps[
            "Driver"
        ]
        ==
        driver

    ].copy()


    d = d[

        d[
            "gap_seconds"
        ]
        .notna()

    ].sort_values(
        "lap_number"
    )


    if len(d) < 2:

        continue


    first_gap = float(

        d[
            "gap_seconds"
        ]
        .iloc[0]

    )


    d[
        "GapChange"
    ] = (

        d[
            "gap_seconds"
        ]

        -

        first_gap

    )


    ax.plot(

        d[
            "lap_number"
        ],

        d[
            "GapChange"
        ],

        linewidth=2.2,

        color=
            driver_colors[
                driver
            ],

        label=(
            f"P{position} {driver}"
        )

    )


ax.axhline(

    0,

    color="black",

    linewidth=1.1

)


ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 RELATIVE GAP EVOLUTION\n"
    "Negative = gained time vs own early-race gap | "
    "Positive = lost time",

    fontsize=16,

    fontweight="bold",

    pad=18

)


ax.set_xlabel(
    "Race Lap"
)


ax.set_ylabel(
    "Change in Gap (seconds)"
)


ax.grid(
    linestyle="--",
    alpha=0.25
)


ax.legend(
    ncol=5,
    fontsize=9,
    loc="best"
)


plt.tight_layout()

plt.show()


# ================================================================
# FINAL GAP SUMMARY
# ================================================================

summary_rows = []


for _, result_row in (
    top10.iterrows()
):

    driver = (
        result_row[
            "Driver"
        ]
    )


    d = gap_laps[

        gap_laps[
            "Driver"
        ]
        ==
        driver

    ]


    d = d[

        d[
            "gap_seconds"
        ]
        .notna()

    ].sort_values(
        "lap_number"
    )


    if d.empty:

        continue


    summary_rows.append({

        "Finish":
            int(
                result_row[
                    "position"
                ]
            ),

        "Driver":
            driver,

        "FirstNumericGap":
            float(
                d[
                    "gap_seconds"
                ]
                .iloc[0]
            ),

        "LastNumericGap":
            float(
                d[
                    "gap_seconds"
                ]
                .iloc[-1]
            ),

        "MinGap":
            float(
                d[
                    "gap_seconds"
                ]
                .min()
            ),

        "MaxGap":
            float(
                d[
                    "gap_seconds"
                ]
                .max()
            )

    })


gap_summary = pd.DataFrame(
    summary_rows
)


gap_summary[
    "NetGapChange"
] = (

    gap_summary[
        "LastNumericGap"
    ]

    -

    gap_summary[
        "FirstNumericGap"
    ]

)


print()
print(
    "=" * 100
)

print(
    "TOP 10 GAP EVOLUTION SUMMARY"
)

print(
    "=" * 100
)


display(
    gap_summary
)


print()
print(
    "NOTE:"
)

print(
    "0s = race leader."
)

print(
    "Semakin tinggi garis utama, "
    "semakin jauh dari leader."
)

print(
    "Jika driver menjadi +1 LAP atau lebih, "
    "OpenF1 dapat mengembalikan gap sebagai string "
    "sehingga bagian tersebut tidak dipaksakan "
    "menjadi jumlah detik."
)
