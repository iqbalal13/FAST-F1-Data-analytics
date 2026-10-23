# ================================================================
# ITALIAN GP 2026 — MONZA
# TOP 10 RACE FINISH GAP
# LOWER BAR = CLOSER TO WINNER
# OPENF1 — GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time
import random
import re
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
                f"⚠️ 429 on {endpoint}; "
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
            "Monza 2026 race tidak ditemukan."
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


name_map = (

    drivers
    .set_index("driver_number")
    ["full_name"]
    .to_dict()

    if "full_name" in drivers.columns

    else {}
)


team_map = (

    drivers
    .set_index("driver_number")
    ["team_name"]
    .to_dict()

    if "team_name" in drivers.columns

    else {}
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


top10["Name"] = (
    top10["driver_number"]
    .map(name_map)
)


top10["Team"] = (
    top10["driver_number"]
    .map(team_map)
)


def parse_gap(value):

    if isinstance(
        value,
        (
            int,
            float,
            np.integer,
            np.floating
        )
    ):

        if pd.isna(value):

            return (
                "unknown",
                np.nan,
                "-"
            )

        return (
            "seconds",
            float(value),
            f"+{float(value):.3f}s"
        )


    text = str(
        value
    ).strip().upper()


    if text in (
        "0",
        "0.0",
        "0.000"
    ):

        return (
            "seconds",
            0.0,
            "WINNER"
        )


    lap_match = re.search(
        r"([0-9]+)\s*LAP",
        text
    )


    if lap_match:

        laps_down = int(
            lap_match.group(1)
        )

        label = (
            f"+{laps_down} LAP"
            +
            (
                "S"
                if laps_down > 1
                else ""
            )
        )

        return (
            "lapped",
            laps_down,
            label
        )


    try:

        value_num = float(
            text.replace(
                "+",
                ""
            )
        )

        return (
            "seconds",
            value_num,
            f"+{value_num:.3f}s"
        )


    except:

        return (
            "other",
            np.nan,
            str(value)
        )


parsed = (
    top10["gap_to_leader"]
    .apply(parse_gap)
)


top10["GapType"] = (
    parsed.apply(
        lambda x:
        x[0]
    )
)


top10["GapNumeric"] = (
    parsed.apply(
        lambda x:
        x[1]
    )
)


top10["GapLabel"] = (
    parsed.apply(
        lambda x:
        x[2]
    )
)


top10.loc[
    top10["position"].eq(1),
    "GapLabel"
] = "WINNER"


top10.loc[
    top10["position"].eq(1),
    "GapNumeric"
] = 0.0


top10.loc[
    top10["position"].eq(1),
    "GapType"
] = "seconds"


max_timed_gap = (

    top10.loc[
        top10["GapType"]
        .eq("seconds"),
        "GapNumeric"
    ]

    .max()
)


if pd.isna(max_timed_gap):

    max_timed_gap = 0.0


lapped_base = (

    max_timed_gap

    +

    max(
        10.0,
        max_timed_gap * 0.12
    )

)


top10["PlotGap"] = (
    top10["GapNumeric"]
)


lapped_rows = (
    top10["GapType"]
    .eq("lapped")
)


for seq, idx in enumerate(
    top10[lapped_rows].index,
    start=1
):

    top10.loc[
        idx,
        "PlotGap"
    ] = (
        lapped_base
        +
        seq * 3.0
    )


other_rows = (
    top10["PlotGap"]
    .isna()
)


for seq, idx in enumerate(
    top10[other_rows].index,
    start=1
):

    top10.loc[
        idx,
        "PlotGap"
    ] = (
        lapped_base
        +
        10
        +
        seq * 3.0
    )


top10["Label"] = (

    "P"

    +

    top10["position"]
    .astype(int)
    .astype(str)

    +

    " - "

    +

    top10["Driver"]
)


winner_duration = pd.to_numeric(

    top10.loc[
        top10["position"]
        .eq(1),
        "duration"
    ],

    errors="coerce"
)


winner_time = (

    format_seconds(
        winner_duration.iloc[0]
    )

    if (
        len(winner_duration)

        and

        pd.notna(
            winner_duration.iloc[0]
        )
    )

    else "-"
)


print(
    "Winner time:",
    winner_time
)


display(

    top10[
        [
            "position",
            "Driver",
            "Name",
            "Team",
            "GapLabel"
        ]
    ]

    .rename(
        columns={
            "position":
                "Pos",

            "GapLabel":
                "Gap to Winner"
        }
    )
)


cmap = plt.colormaps[
    "tab10"
]


colors = [

    cmap(i)

    for i in range(
        len(top10)
    )

]


fig, ax = plt.subplots(
    figsize=(12, 7)
)


bars = ax.barh(

    top10["Label"],

    top10["PlotGap"],

    color=colors
)


ax.invert_yaxis()


margin = max(

    top10["PlotGap"]
    .max()

    *
    0.02,

    0.6
)


for bar, (_, row) in zip(
    bars,
    top10.iterrows()
):

    x = (
        row["PlotGap"]
        +
        margin
    )


    if row["position"] == 1:

        x = margin


    ax.text(

        x,

        bar.get_y()
        +
        bar.get_height() / 2,

        row["GapLabel"],

        va="center",

        fontsize=9,

        fontweight="bold"
    )


ax.set_xlabel(

    "Gap Representation "
    "(seconds for timed finishers)"
)

ax.set_ylabel(
    "Driver"
)

ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "TOP 10 RACE FINISH GAP\n"

    f"Winner time: {winner_time} | "
    "Lower = closer to winner",

    fontsize=15,

    fontweight="bold"
)

ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)


plt.tight_layout()

plt.show()
