# ================================================================
# ITALIAN GP 2026 — MONZA
# Q3 TABLE + Q3 TIME GRAPH + GAP TO POLE
# OPENF1 — GOOGLE COLAB — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time
import random
import ast
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

            LAST_REQUEST_TIME = time.time()

        except requests.RequestException as e:

            wait = min(
                3 + attempt * 3,
                30
            )

            print(
                f"\nNetwork error [{endpoint}]: {e}"
            )

            print(
                f"Retry dalam {wait}s..."
            )

            time.sleep(wait)

            continue


        if r.status_code == 429:

            retry_after = r.headers.get(
                "Retry-After"
            )

            if retry_after:

                try:
                    wait = float(retry_after)

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
                f"\n⚠️ OpenF1 rate limit 429 pada {endpoint}."
            )

            print(
                f"Retry {attempt + 1}/{max_retries} "
                f"dalam {wait:.1f}s..."
            )

            time.sleep(wait)

            continue


        if r.status_code != 200:

            print("\nOPENF1 API ERROR")
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


    raise RuntimeError(
        f"OpenF1 gagal setelah "
        f"{max_retries} retry pada {endpoint}"
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

    minutes = int(
        float(seconds) // 60
    )

    sec = float(seconds) % 60

    return f"{minutes}:{sec:06.3f}"


def find_monza_session(session_name):

    sessions = pd.DataFrame(
        api_get(
            "sessions",
            {"year": YEAR}
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

    country = (
        sessions["country_name"]
        if "country_name" in sessions.columns
        else pd.Series(
            "",
            index=sessions.index
        )
    )


    monza_mask = (

        location.astype(str).str.contains(
            "Monza",
            case=False,
            na=False
        )

        |

        circuit.astype(str).str.contains(
            "Monza",
            case=False,
            na=False
        )

        |

        (
            country.astype(str).str.contains(
                "Italy",
                case=False,
                na=False
            )

            &

            location.astype(str).str.contains(
                "Monza",
                case=False,
                na=False
            )
        )
    )


    monza = sessions[
        monza_mask
    ].copy()


    if monza.empty:

        raise RuntimeError(
            "Session Monza 2026 tidak ditemukan."
        )


    selected = monza[

        monza["session_name"]
        .astype(str)
        .str.lower()
        .eq(
            session_name.lower()
        )

    ].copy()


    if selected.empty:

        raise RuntimeError(
            f"Session {session_name} "
            f"Monza 2026 tidak ditemukan."
        )


    selected["_parsed_start"] = parse_dt(
        selected["date_start"]
    )


    return (
        selected
        .sort_values("_parsed_start")
        .iloc[-1]
    )


def load_driver_maps(session_key):

    drivers = pd.DataFrame(
        api_get(
            "drivers",
            {
                "session_key":
                    int(session_key)
            }
        )
    )


    drivers["driver_number"] = pd.to_numeric(
        drivers["driver_number"],
        errors="coerce"
    )


    drivers = drivers.dropna(
        subset=["driver_number"]
    ).copy()


    drivers["driver_number"] = (
        drivers["driver_number"]
        .astype(int)
    )


    drivers = drivers.drop_duplicates(
        "driver_number"
    )


    acronym = (
        drivers
        .set_index("driver_number")
        ["name_acronym"]
        .to_dict()
    )


    full_name = (
        drivers
        .set_index("driver_number")
        ["full_name"]
        .to_dict()

        if "full_name" in drivers.columns

        else {}
    )


    team = (
        drivers
        .set_index("driver_number")
        ["team_name"]
        .to_dict()

        if "team_name" in drivers.columns

        else {}
    )


    return (
        drivers,
        acronym,
        full_name,
        team
    )


def extract_q3(value):

    if isinstance(
        value,
        (list, tuple, np.ndarray)
    ):

        return (
            value[2]
            if len(value) >= 3
            else np.nan
        )


    if isinstance(value, str):

        try:

            parsed = ast.literal_eval(
                value
            )

            if (
                isinstance(
                    parsed,
                    (list, tuple)
                )

                and

                len(parsed) >= 3
            ):

                return parsed[2]

        except:
            pass


    return np.nan


print("=" * 80)
print("ITALIAN GP 2026 — MONZA — QUALIFYING Q3")
print("=" * 80)


session = find_monza_session(
    "Qualifying"
)

SESSION_KEY = int(
    session["session_key"]
)


print(
    "Session Key :",
    SESSION_KEY
)

print(
    "Location    :",
    session.get(
        "location",
        "Monza"
    )
)

print(
    "Circuit     :",
    session.get(
        "circuit_short_name",
        "Monza"
    )
)


drivers, driver_map, full_name_map, team_map = (
    load_driver_maps(
        SESSION_KEY
    )
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


results["Q3Seconds"] = (
    results["duration"]
    .apply(
        extract_q3
    )
)


q3 = results[

    results["position"]
    .between(1, 10)

    &

    results["Q3Seconds"]
    .notna()

].copy()


q3["driver_number"] = (
    q3["driver_number"]
    .astype(int)
)


q3["Driver"] = (
    q3["driver_number"]
    .map(driver_map)
)


q3["Name"] = (
    q3["driver_number"]
    .map(full_name_map)
)


q3["Team"] = (
    q3["driver_number"]
    .map(team_map)
)


q3["Q3 Time"] = (
    q3["Q3Seconds"]
    .apply(
        format_seconds
    )
)


q3 = (
    q3
    .sort_values("position")
    .reset_index(drop=True)
)


if q3.empty:

    raise RuntimeError(
        "Tidak ada hasil Q3 Monza 2026."
    )


# ================================================================
# TABLE P10 -> P1
# ================================================================

print("\n" + "=" * 80)
print("Q3 RESULT — P10 -> P1")
print("=" * 80)


q3_table = (

    q3

    .sort_values(
        "position",
        ascending=False
    )

    [
        [
            "position",
            "Driver",
            "Name",
            "Team",
            "Q3 Time"
        ]
    ]

    .rename(
        columns={
            "position":
                "Pos"
        }
    )

    .copy()
)


q3_table["Pos"] = (
    q3_table["Pos"]
    .astype(int)
)


display(
    q3_table
)


# ================================================================
# GRAPH DATA
# ================================================================

pole_time = (
    q3["Q3Seconds"]
    .min()
)


q3["DeltaToPole"] = (
    q3["Q3Seconds"]
    -
    pole_time
)


q3["Label"] = (

    "P"

    +

    q3["position"]
    .astype(int)
    .astype(str)

    +

    " - "

    +

    q3["Driver"]
    .astype(str)
)


cmap = plt.colormaps[
    "tab10"
]


driver_colors = {

    driver:
        cmap(i)

    for i, driver

    in enumerate(
        q3["Driver"].tolist()
    )
}


colors = [

    driver_colors[d]

    for d in q3["Driver"]

]


# ================================================================
# GRAPH 1 — ABSOLUTE Q3 TIME
# ================================================================

fig, ax = plt.subplots(
    figsize=(11, 6)
)


bars = ax.barh(

    q3["Label"],

    q3["Q3Seconds"],

    color=colors
)


ax.invert_yaxis()


for bar, (_, row) in zip(
    bars,
    q3.iterrows()
):

    ax.text(

        row["Q3Seconds"] + 0.02,

        bar.get_y()
        +
        bar.get_height() / 2,

        row["Q3 Time"],

        va="center",

        fontsize=9,

        fontweight="bold"
    )


ax.set_xlabel(
    "Q3 Lap Time (seconds)"
)

ax.set_ylabel(
    "Driver"
)

ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "Q3 Qualifying Times — P1 to P10",

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


# ================================================================
# GRAPH 2 — GAP TO POLE
# ================================================================

fig, ax = plt.subplots(
    figsize=(11, 6)
)


bars = ax.barh(

    q3["Label"],

    q3["DeltaToPole"],

    color=colors
)


ax.invert_yaxis()


for bar, (_, row) in zip(
    bars,
    q3.iterrows()
):

    delta = float(
        row["DeltaToPole"]
    )


    if abs(delta) < 1e-9:

        text = "POLE"
        x = 0.01

    else:

        text = (
            f"+{delta:.3f}s"
        )

        x = (
            delta
            +
            0.006
        )


    ax.text(

        x,

        bar.get_y()
        +
        bar.get_height() / 2,

        text,

        va="center",

        fontsize=9,

        fontweight="bold"
    )


ax.set_xlim(

    0,

    max(
        q3["DeltaToPole"].max()
        *
        1.18,

        0.15
    )
)


ax.set_xlabel(
    "Gap to Pole (seconds)"
)

ax.set_ylabel(
    "Driver"
)

ax.set_title(

    "ITALIAN GP 2026 — MONZA\n"
    "Q3 Gap to Pole — P1 to P10",

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
