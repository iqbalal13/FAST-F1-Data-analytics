# ================================================================
# ITALIAN GP 2026 — MONZA
# Q3 P1 -> P10 — SINGLE CLEAN GRAPH
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
                f"⚠️ 429 {endpoint}; "
                f"retry {attempt+1}/{max_retries} "
                f"dalam {wait:.1f}s"
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
                f"OpenF1 HTTP {r.status_code}"
            )


        data = r.json()

        if not data and not allow_empty:

            raise RuntimeError(
                f"No data from {endpoint}"
            )


        return data


    raise RuntimeError(
        f"OpenF1 gagal: {endpoint}"
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


def find_monza_session():

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


session = find_monza_session()

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


drivers = (
    drivers
    .dropna(
        subset=["driver_number"]
    )
)


drivers["driver_number"] = (
    drivers["driver_number"]
    .astype(int)
)


driver_map = (

    drivers
    .drop_duplicates("driver_number")
    .set_index("driver_number")
    ["name_acronym"]
    .to_dict()
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


q3 = (
    q3
    .sort_values("position")
    .reset_index(drop=True)
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
)


cmap = plt.colormaps[
    "tab10"
]


colors = [

    cmap(i)

    for i in range(
        len(q3)
    )

]


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

        format_seconds(
            row["Q3Seconds"]
        ),

        va="center",

        fontsize=10,

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
