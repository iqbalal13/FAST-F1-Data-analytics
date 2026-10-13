# ================================================================
# AZERBAIJAN GP 2026 — BAKU
# Q3 FASTEST SECTORS + CIRCUIT MAP
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

from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


# ================================================================
# CONFIG
# ================================================================

YEAR = 2026
BASE = "https://api.openf1.org/v1"

LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 0.45


# ================================================================
# RATE LIMIT SAFE API HELPER
# ================================================================

def api_get(endpoint, params=None, allow_empty=False, max_retries=8):

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

            r = requests.get(
                url,
                params=params,
                timeout=90,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
            )

            LAST_REQUEST_TIME = time.time()


        except requests.RequestException as e:

            wait = min(
                2 ** attempt,
                15
            )

            print(
                f"Network error: {e}"
            )

            print(
                f"Retry dalam {wait}s..."
            )

            time.sleep(wait)

            continue


        # --------------------------------------------------------
        # RATE LIMIT
        # --------------------------------------------------------

        if r.status_code == 429:

            retry_after = r.headers.get(
                "Retry-After"
            )

            if retry_after is not None:

                try:

                    wait = float(
                        retry_after
                    )

                except:
                    wait = min(
                        2 ** attempt,
                        15
                    )

            else:

                wait = min(
                    2 ** attempt,
                    15
                )


            wait += random.uniform(
                0.2,
                0.7
            )


            print(
                f"⚠️ OpenF1 rate limit 429."
            )

            print(
                f"Retry {attempt + 1}/{max_retries} "
                f"dalam {wait:.1f}s..."
            )

            time.sleep(wait)

            continue


        # --------------------------------------------------------
        # OTHER HTTP ERRORS
        # --------------------------------------------------------

        if r.status_code != 200:

            print("\nAPI ERROR")
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
                f"No data returned from {endpoint}"
            )

        return data


    raise RuntimeError(
        f"OpenF1 gagal setelah {max_retries} retry: {endpoint}"
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
# 1. LOAD ALL 2026 SESSIONS
# ================================================================

print("=" * 75)
print("LOAD 2026 SESSIONS")
print("=" * 75)


sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)


print(
    "Total 2026 sessions:",
    len(sessions)
)


# ================================================================
# 2. FIND BAKU
# ================================================================

location_col = (
    sessions["location"]
    if "location" in sessions.columns
    else pd.Series("", index=sessions.index)
)


circuit_col = (
    sessions["circuit_short_name"]
    if "circuit_short_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)


country_col = (
    sessions["country_name"]
    if "country_name" in sessions.columns
    else pd.Series("", index=sessions.index)
)


baku_mask = (

    location_col.astype(str).str.contains(
        "Baku",
        case=False,
        na=False
    )

    |

    circuit_col.astype(str).str.contains(
        "Baku",
        case=False,
        na=False
    )

    |

    country_col.astype(str).str.contains(
        "Azerbaijan",
        case=False,
        na=False
    )
)


baku_sessions = sessions[
    baku_mask
].copy()


print("\nMatching sessions:")

display(
    baku_sessions[
        [
            "session_key",
            "session_name",
            "country_name",
            "location",
            "circuit_short_name",
            "date_start",
            "date_end"
        ]
    ]
)


if baku_sessions.empty:

    raise RuntimeError(
        "Azerbaijan / Baku session tidak ditemukan."
    )


# ================================================================
# 3. FIND QUALIFYING
# ================================================================

qualifying = baku_sessions[

    baku_sessions["session_name"]
    .astype(str)
    .str.lower()
    .eq("qualifying")

].copy()


if qualifying.empty:

    raise RuntimeError(
        "Baku qualifying tidak ditemukan."
    )


qualifying["parsed_start"] = parse_dt(
    qualifying["date_start"]
)


qualifying = qualifying.sort_values(
    "parsed_start"
)


session = qualifying.iloc[-1]


SESSION_KEY = int(
    session["session_key"]
)

MEETING_KEY = int(
    session["meeting_key"]
)


SESSION_START = parse_dt(
    session["date_start"]
)

SESSION_END = parse_dt(
    session["date_end"]
)


print("\n" + "=" * 75)
print("QUALIFYING FOUND")
print("=" * 75)

print(
    "Session Key :",
    SESSION_KEY
)

print(
    "Meeting Key :",
    MEETING_KEY
)

print(
    "Location    :",
    session["location"]
)

print(
    "Country     :",
    session["country_name"]
)

print(
    "Circuit     :",
    session["circuit_short_name"]
)

print(
    "Start       :",
    SESSION_START
)

print(
    "End         :",
    SESSION_END
)


# ================================================================
# 4. DRIVER DATA
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
# 5. RACE CONTROL
# ================================================================

race_control_data = api_get(
    "race_control",
    {
        "session_key":
            SESSION_KEY
    },
    allow_empty=True
)


race_control = pd.DataFrame(
    race_control_data
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
            race_control["phase"] == 3
        ].copy()


        q3_control = q3_control[
            q3_control["date_parsed"].notna()
        ]


        if not q3_control.empty:

            Q3_START = (
                q3_control[
                    "date_parsed"
                ].min()
            )


            print(
                "\nQ3 marker ditemukan:",
                Q3_START
            )


# ================================================================
# FALLBACK Q3 WINDOW
# ================================================================

if Q3_START is None:

    Q3_START = (
        SESSION_END
        -
        pd.Timedelta(
            minutes=15
        )
    )


    print(
        "\n⚠️ Q3 marker tidak tersedia."
    )

    print(
        "Fallback ke 15 menit terakhir qualifying."
    )


Q3_FILTER_START = (
    Q3_START
    -
    pd.Timedelta(
        seconds=15
    )
)


Q3_FILTER_END = (
    SESSION_END
    +
    pd.Timedelta(
        minutes=3
    )
)


# ================================================================
# 6. LOAD QUALIFYING LAPS
# ================================================================

print("\n" + "=" * 75)
print("LOAD LAP DATA")
print("=" * 75)


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


laps = laps[
    laps["date_parsed"].notna()
].copy()


# ================================================================
# 7. FILTER Q3
# ================================================================

q3 = laps[

    (
        laps["date_parsed"]
        >=
        Q3_FILTER_START
    )

    &

    (
        laps["date_parsed"]
        <=
        Q3_FILTER_END
    )

].copy()


if "is_pit_out_lap" in q3.columns:

    q3 = q3[
        q3["is_pit_out_lap"] != True
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
        "Tidak ada valid timed lap Q3."
    )


q3["Driver"] = q3[
    "driver_number"
].map(
    driver_map
)


q3["Driver"] = q3[
    "Driver"
].fillna(
    q3[
        "driver_number"
    ].astype(str)
)


print(
    "Valid Q3 laps:",
    len(q3)
)

print(
    "Drivers:",
    sorted(
        q3[
            "Driver"
        ].unique()
    )
)


# ================================================================
# 8. FASTEST INDIVIDUAL SECTOR
# ================================================================

sector_columns = {
    "S1": "duration_sector_1",
    "S2": "duration_sector_2",
    "S3": "duration_sector_3"
}


sector_results = []


for sector, column in sector_columns.items():

    idx = q3[
        column
    ].idxmin()


    row = q3.loc[
        idx
    ]


    sector_results.append({

        "Sector":
            sector,

        "Driver":
            row["Driver"],

        "DriverNumber":
            int(
                row[
                    "driver_number"
                ]
            ),

        "Lap":
            int(
                row[
                    "lap_number"
                ]
            ),

        "Time":
            float(
                row[
                    column
                ]
            )
    })


sector_df = pd.DataFrame(
    sector_results
)


print("\n" + "=" * 75)
print("FASTEST Q3 SECTORS")
print("=" * 75)


sector_table = sector_df.copy()


sector_table["Time"] = (
    sector_table["Time"]
    .map(
        lambda x:
        f"{x:.3f} s"
    )
)


display(
    sector_table
)


# ================================================================
# 9. FASTEST COMPLETE Q3 LAP
# ================================================================

complete = q3[
    q3["lap_duration"].notna()
].copy()


complete = complete[
    complete["lap_duration"] > 0
]


if complete.empty:

    q3["calculated_time"] = (

        q3["duration_sector_1"]
        +
        q3["duration_sector_2"]
        +
        q3["duration_sector_3"]

    )


    fastest = q3.loc[
        q3[
            "calculated_time"
        ].idxmin()
    ]


    FASTEST_TIME = float(
        fastest[
            "calculated_time"
        ]
    )


else:

    fastest = complete.loc[
        complete[
            "lap_duration"
        ].idxmin()
    ]


    FASTEST_TIME = float(
        fastest[
            "lap_duration"
        ]
    )


FASTEST_DRIVER_NUM = int(
    fastest[
        "driver_number"
    ]
)


FASTEST_DRIVER = driver_map.get(
    FASTEST_DRIVER_NUM,
    str(
        FASTEST_DRIVER_NUM
    )
)


FASTEST_LAP = int(
    fastest[
        "lap_number"
    ]
)


print("\n" + "=" * 75)
print("FASTEST Q3 LAP")
print("=" * 75)

print(
    "Driver:",
    FASTEST_DRIVER
)

print(
    "Lap   :",
    FASTEST_LAP
)

print(
    "Time  :",
    f"{FASTEST_TIME:.3f} s"
)


# ================================================================
# 10. LAP START / END
# ================================================================

lap_start = parse_dt(
    fastest[
        "date_start"
    ]
)


if pd.isna(lap_start):

    raise RuntimeError(
        "Fastest lap start time invalid."
    )


lap_end = (
    lap_start
    +
    pd.Timedelta(
        seconds=FASTEST_TIME
    )
)


# ================================================================
# 11. LOAD LOCATION DATA
#
# HANYA window fastest lap
# ================================================================

print("\n" + "=" * 75)
print("LOAD TRACK LOCATION DATA")
print("=" * 75)


LOCATION_START = (
    lap_start
    -
    pd.Timedelta(
        seconds=2
    )
)


LOCATION_END = (
    lap_end
    +
    pd.Timedelta(
        seconds=2
    )
)


print(
    "Location window:",
    LOCATION_START,
    "->",
    LOCATION_END
)


location = pd.DataFrame(
    api_get(
        "location",
        {
            "session_key":
                SESSION_KEY,

            "driver_number":
                FASTEST_DRIVER_NUM,

            "date>":
                LOCATION_START.isoformat(),

            "date<":
                LOCATION_END.isoformat()
        }
    )
)


print(
    "Location points downloaded:",
    len(location)
)


# ================================================================
# 12. PREP LOCATION
# ================================================================

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


location = location.dropna(
    subset=[
        "date_parsed",
        "x",
        "y"
    ]
)


location = location.sort_values(
    "date_parsed"
)


# ================================================================
# 13. FILTER ACTUAL FASTEST LAP
# ================================================================

track = location[

    (
        location[
            "date_parsed"
        ]
        >=
        lap_start
    )

    &

    (
        location[
            "date_parsed"
        ]
        <=
        lap_end
    )

].copy()


track["elapsed"] = (

    track[
        "date_parsed"
    ]

    -

    lap_start

).dt.total_seconds()


print(
    "Track points:",
    len(track)
)


if len(track) < 20:

    raise RuntimeError(
        f"Location points terlalu sedikit: {len(track)}"
    )


# ================================================================
# 14. FASTEST LAP SECTOR BOUNDARIES
# ================================================================

lap_s1 = float(
    fastest[
        "duration_sector_1"
    ]
)


lap_s2 = float(
    fastest[
        "duration_sector_2"
    ]
)


lap_s3 = float(
    fastest[
        "duration_sector_3"
    ]
)


S1_END = lap_s1

S2_END = (
    lap_s1
    +
    lap_s2
)


print()
print(
    "Fastest lap S1:",
    f"{lap_s1:.3f}s"
)

print(
    "Fastest lap S2:",
    f"{lap_s2:.3f}s"
)

print(
    "Fastest lap S3:",
    f"{lap_s3:.3f}s"
)


# ================================================================
# 15. XY DATA
# ================================================================

x = track[
    "x"
].to_numpy(
    dtype=float
)


y = track[
    "y"
].to_numpy(
    dtype=float
)


elapsed = track[
    "elapsed"
].to_numpy(
    dtype=float
)


# Remove consecutive duplicate coordinate points

valid = np.ones(
    len(x),
    dtype=bool
)


valid[1:] = (

    (np.diff(x) != 0)

    |

    (np.diff(y) != 0)

)


x = x[valid]
y = y[valid]
elapsed = elapsed[valid]


# ================================================================
# 16. TRACK SEGMENTS
# ================================================================

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


# ================================================================
# 17. SECTOR COLORS
# ================================================================

sector_colors = []


for sec in elapsed[:-1]:

    if sec <= S1_END:

        sector_colors.append(
            "red"
        )

    elif sec <= S2_END:

        sector_colors.append(
            "green"
        )

    else:

        sector_colors.append(
            "blue"
        )


# ================================================================
# 18. PLOT BAKU MAP
# ================================================================

fig, ax = plt.subplots(
    figsize=(14, 8)
)


track_collection = LineCollection(
    segments,
    colors=sector_colors,
    linewidth=7,
    capstyle="round",
    joinstyle="round"
)


ax.add_collection(
    track_collection
)


ax.set_aspect(
    "equal",
    adjustable="box"
)


# ================================================================
# 19. LIMITS
# ================================================================

mx = (
    x.max()
    -
    x.min()
) * 0.08


my = (
    y.max()
    -
    y.min()
) * 0.08


ax.set_xlim(
    x.min() - mx,
    x.max() + mx
)


ax.set_ylim(
    y.min() - my,
    y.max() + my
)


# ================================================================
# 20. START / FINISH
# ================================================================

ax.scatter(
    x[0],
    y[0],
    s=170,
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
    fontweight="bold",
    zorder=11
)


# ================================================================
# 21. FASTEST SECTOR RESULT
# ================================================================

s1 = sector_df[
    sector_df["Sector"] == "S1"
].iloc[0]


s2 = sector_df[
    sector_df["Sector"] == "S2"
].iloc[0]


s3 = sector_df[
    sector_df["Sector"] == "S3"
].iloc[0]


# ================================================================
# 22. TITLE
# ================================================================

ax.set_title(

    "AZERBAIJAN GP 2026 — BAKU Q3 FASTEST SECTORS\n"

    f"S1: {s1['Driver']} {s1['Time']:.3f}s   |   "

    f"S2: {s2['Driver']} {s2['Time']:.3f}s   |   "

    f"S3: {s3['Driver']} {s3['Time']:.3f}s",

    fontsize=16,
    fontweight="bold",
    pad=20
)


# ================================================================
# 23. LEGEND
# ================================================================

legend_elements = [

    Line2D(
        [0], [0],
        color="red",
        lw=7,
        label=(
            f"Sector 1 — "
            f"{s1['Driver']} "
            f"{s1['Time']:.3f}s"
        )
    ),

    Line2D(
        [0], [0],
        color="green",
        lw=7,
        label=(
            f"Sector 2 — "
            f"{s2['Driver']} "
            f"{s2['Time']:.3f}s"
        )
    ),

    Line2D(
        [0], [0],
        color="blue",
        lw=7,
        label=(
            f"Sector 3 — "
            f"{s3['Driver']} "
            f"{s3['Time']:.3f}s"
        )
    ),

    Line2D(
        [0], [0],
        marker="o",
        markerfacecolor="white",
        markeredgecolor="black",
        linestyle="None",
        markersize=9,
        label="Start / Finish"
    )
]


ax.legend(
    handles=legend_elements,
    loc="best",
    fontsize=10
)


ax.axis(
    "off"
)


plt.tight_layout()
plt.show()
