# ================================================================
# ITALIAN GP 2026 — MONZA
# Q3 FASTEST SECTORS + CIRCUIT MAP
# OPENF1 — GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time
import random
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from matplotlib.collections import LineCollection
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
                f"retry dalam {wait:.1f}s"
            )

            time.sleep(wait)

            continue


        if r.status_code != 200:

            print("\nAPI ERROR")
            print(r.url)
            print(r.status_code)
            print(r.text[:500])

            raise RuntimeError(
                f"OpenF1 HTTP {r.status_code}"
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


def find_monza_qualifying():

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


    monza = sessions[
        mask
    ].copy()


    qualifying = monza[

        monza["session_name"]
        .astype(str)
        .str.lower()
        .eq("qualifying")

    ].copy()


    if qualifying.empty:

        raise RuntimeError(
            "Monza qualifying tidak ditemukan."
        )


    qualifying["_date"] = parse_dt(
        qualifying["date_start"]
    )


    return (
        qualifying
        .sort_values("_date")
        .iloc[-1]
    )


print("=" * 80)
print("ITALIAN GP 2026 — MONZA — Q3 FASTEST SECTORS")
print("=" * 80)


session = find_monza_qualifying()

SESSION_KEY = int(
    session["session_key"]
)

SESSION_END = parse_dt(
    session["date_end"]
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


# ================================================================
# OFFICIAL Q3 DRIVERS
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


Q3_DRIVERS = (

    results[
        results["position"]
        .between(1, 10)
    ]

    ["driver_number"]

    .dropna()

    .astype(int)

    .tolist()
)


# ================================================================
# DETECT Q3 START
# ================================================================

race_control = pd.DataFrame(
    api_get(
        "race_control",
        {
            "session_key":
                SESSION_KEY
        },
        allow_empty=True
    )
)


Q3_START = None


if not race_control.empty:

    race_control["date_parsed"] = parse_dt(
        race_control["date"]
    )


    if "qualifying_phase" in race_control.columns:

        race_control["phase"] = pd.to_numeric(
            race_control["qualifying_phase"],
            errors="coerce"
        )


        q3_control = race_control[

            race_control["phase"]
            .eq(3)

            &

            race_control["date_parsed"]
            .notna()

        ]


        if not q3_control.empty:

            Q3_START = (
                q3_control[
                    "date_parsed"
                ].min()
            )


if Q3_START is None:

    Q3_START = (
        SESSION_END
        -
        pd.Timedelta(
            minutes=15
        )
    )


print(
    "Session Key:",
    SESSION_KEY
)

print(
    "Q3 Start   :",
    Q3_START
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
    "lap_duration",
    "duration_sector_1",
    "duration_sector_2",
    "duration_sector_3"
]:

    if col in laps.columns:

        laps[col] = pd.to_numeric(
            laps[col],
            errors="coerce"
        )


laps["date_parsed"] = parse_dt(
    laps["date_start"]
)


q3 = laps[

    laps["driver_number"]
    .isin(Q3_DRIVERS)

    &

    laps["date_parsed"]
    .between(
        Q3_START
        -
        pd.Timedelta(seconds=20),
        SESSION_END
        +
        pd.Timedelta(minutes=3)
    )

].copy()


if "is_pit_out_lap" in q3.columns:

    q3 = q3[
        q3["is_pit_out_lap"]
        != True
    ].copy()


q3 = q3.dropna(
    subset=[
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3"
    ]
)


q3 = q3[

    (q3["duration_sector_1"] > 0)

    &

    (q3["duration_sector_2"] > 0)

    &

    (q3["duration_sector_3"] > 0)

].copy()


if q3.empty:

    raise RuntimeError(
        "Tidak ada Q3 sector data."
    )


q3["Driver"] = (
    q3["driver_number"]
    .map(driver_map)
)


sector_cols = {
    "S1": "duration_sector_1",
    "S2": "duration_sector_2",
    "S3": "duration_sector_3"
}


sector_rows = []


for sector, col in sector_cols.items():

    idx = q3[col].idxmin()

    row = q3.loc[idx]

    sector_rows.append({

        "Sector":
            sector,

        "Driver":
            row["Driver"],

        "DriverNumber":
            int(
                row["driver_number"]
            ),

        "Lap":
            int(
                row["lap_number"]
            ),

        "Time":
            float(
                row[col]
            )
    })


sector_df = pd.DataFrame(
    sector_rows
)


display(
    sector_df
)


# ================================================================
# FASTEST FULL Q3 LAP
# ================================================================

complete = q3[

    q3["lap_duration"]
    .notna()

    &

    (q3["lap_duration"] > 0)

].copy()


if complete.empty:

    q3["calculated"] = (

        q3["duration_sector_1"]

        +

        q3["duration_sector_2"]

        +

        q3["duration_sector_3"]

    )


    fastest = q3.loc[
        q3["calculated"]
        .idxmin()
    ]

    FASTEST_TIME = float(
        fastest["calculated"]
    )

else:

    fastest = complete.loc[
        complete["lap_duration"]
        .idxmin()
    ]

    FASTEST_TIME = float(
        fastest["lap_duration"]
    )


FASTEST_DRIVER_NUM = int(
    fastest["driver_number"]
)


FASTEST_DRIVER = driver_map.get(
    FASTEST_DRIVER_NUM,
    str(FASTEST_DRIVER_NUM)
)


lap_start = parse_dt(
    fastest["date_start"]
)


lap_end = (

    lap_start

    +

    pd.Timedelta(
        seconds=FASTEST_TIME
    )
)


print()
print(
    "Fastest Q3 lap:",
    FASTEST_DRIVER,
    format_seconds(
        FASTEST_TIME
    )
)


# ================================================================
# LOCATION ONLY AROUND LAP
# ================================================================

location = pd.DataFrame(
    api_get(
        "location",
        {
            "session_key":
                SESSION_KEY,

            "driver_number":
                FASTEST_DRIVER_NUM,

            "date>":
                (
                    lap_start
                    -
                    pd.Timedelta(seconds=2)
                ).isoformat(),

            "date<":
                (
                    lap_end
                    +
                    pd.Timedelta(seconds=2)
                ).isoformat()
        }
    )
)


location["date_parsed"] = parse_dt(
    location["date"]
)


location["x"] = pd.to_numeric(
    location["x"],
    errors="coerce"
)


location["y"] = pd.to_numeric(
    location["y"],
    errors="coerce"
)


location = (

    location

    .dropna(
        subset=[
            "date_parsed",
            "x",
            "y"
        ]
    )

    .sort_values(
        "date_parsed"
    )
)


location = location[

    ~(
        (location["x"] == 0)
        &
        (location["y"] == 0)
    )

]


track = location[

    location["date_parsed"]
    .between(
        lap_start,
        lap_end
    )

].copy()


if len(track) < 20:

    raise RuntimeError(
        f"Location points terlalu sedikit: "
        f"{len(track)}"
    )


track["elapsed"] = (

    track["date_parsed"]

    -

    lap_start

).dt.total_seconds()


lap_s1 = float(
    fastest["duration_sector_1"]
)

lap_s2 = float(
    fastest["duration_sector_2"]
)

lap_s3 = float(
    fastest["duration_sector_3"]
)


S1_END = lap_s1

S2_END = (
    lap_s1
    +
    lap_s2
)


x = track["x"].to_numpy(
    dtype=float
)

y = track["y"].to_numpy(
    dtype=float
)

elapsed = track["elapsed"].to_numpy(
    dtype=float
)


valid = np.ones(
    len(x),
    dtype=bool
)


if len(x) > 1:

    valid[1:] = (

        (np.diff(x) != 0)

        |

        (np.diff(y) != 0)

    )


x = x[valid]
y = y[valid]
elapsed = elapsed[valid]


points = np.array(
    [x, y]
).T.reshape(
    -1,
    1,
    2
)


segments = np.concatenate(
    [
        points[:-1],
        points[1:]
    ],
    axis=1
)


colors = []


for t in elapsed[:-1]:

    if t <= S1_END:

        colors.append(
            "red"
        )

    elif t <= S2_END:

        colors.append(
            "green"
        )

    else:

        colors.append(
            "blue"
        )


# ================================================================
# GRAPH — MONZA MAP
# ================================================================

fig, ax = plt.subplots(
    figsize=(14, 9)
)


lc = LineCollection(
    segments,
    colors=colors,
    linewidth=7,
    capstyle="round",
    joinstyle="round"
)


ax.add_collection(
    lc
)


ax.set_aspect(
    "equal",
    adjustable="box"
)


mx = max(
    (x.max() - x.min()) * 0.08,
    100
)

my = max(
    (y.max() - y.min()) * 0.08,
    100
)


ax.set_xlim(
    x.min() - mx,
    x.max() + mx
)

ax.set_ylim(
    y.min() - my,
    y.max() + my
)


ax.scatter(
    x[0],
    y[0],
    s=160,
    facecolor="white",
    edgecolor="black",
    linewidth=2,
    zorder=10
)


ax.text(
    x[0],
    y[0],
    "  S/F",
    fontsize=10,
    fontweight="bold"
)


s1 = sector_df[
    sector_df["Sector"]
    .eq("S1")
].iloc[0]


s2 = sector_df[
    sector_df["Sector"]
    .eq("S2")
].iloc[0]


s3 = sector_df[
    sector_df["Sector"]
    .eq("S3")
].iloc[0]


ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "Q3 FASTEST SECTORS\n"

    f"S1: {s1['Driver']} "
    f"{s1['Time']:.3f}s   |   "

    f"S2: {s2['Driver']} "
    f"{s2['Time']:.3f}s   |   "

    f"S3: {s3['Driver']} "
    f"{s3['Time']:.3f}s",

    fontsize=15,

    fontweight="bold",

    pad=18
)


legend = [

    Line2D(
        [0], [0],
        color="red",
        lw=7,
        label=(
            f"S1 — {s1['Driver']} "
            f"{s1['Time']:.3f}s"
        )
    ),

    Line2D(
        [0], [0],
        color="green",
        lw=7,
        label=(
            f"S2 — {s2['Driver']} "
            f"{s2['Time']:.3f}s"
        )
    ),

    Line2D(
        [0], [0],
        color="blue",
        lw=7,
        label=(
            f"S3 — {s3['Driver']} "
            f"{s3['Time']:.3f}s"
        )
    )
]


ax.legend(
    handles=legend,
    loc="best",
    fontsize=10
)


ax.axis(
    "off"
)


plt.tight_layout()

plt.show()
