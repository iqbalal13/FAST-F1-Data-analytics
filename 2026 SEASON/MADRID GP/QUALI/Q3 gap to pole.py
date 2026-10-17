# ================================================================
# MADRID GP 2026 — Q3 P1 -> P10
# SINGLE CLEAN GRAPH — STANDALONE CELL
# OPENF1
# ================================================================

!pip install -q requests pandas numpy matplotlib


import time
import random
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
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        try:
            r = http.get(url, params=params, timeout=90)
            LAST_REQUEST_TIME = time.time()
        except requests.RequestException as e:
            wait = min(3 + attempt * 3, 30)
            print(f"\nNetwork error [{endpoint}]: {e}")
            print(f"Retry dalam {wait}s...")
            time.sleep(wait)
            continue

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = float(retry_after)
                except Exception:
                    wait = min(4 + attempt * 4, 40)
            else:
                wait = min(4 + attempt * 4, 40)

            wait += random.uniform(0.3, 1.0)
            print(f"\n⚠️ OpenF1 rate limit 429 pada {endpoint}.")
            print(f"Retry {attempt + 1}/{max_retries} dalam {wait:.1f}s...")
            time.sleep(wait)
            continue

        if r.status_code != 200:
            print("\nOPENF1 API ERROR")
            print("URL    :", r.url)
            print("Status :", r.status_code)
            print("Body   :", r.text[:500])
            raise RuntimeError(f"OpenF1 HTTP {r.status_code}")

        data = r.json()
        if not data and not allow_empty:
            raise RuntimeError(f"No data returned from {endpoint}")

        return data

    raise RuntimeError(
        f"OpenF1 gagal setelah {max_retries} retry pada endpoint {endpoint}"
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
    minutes = int(float(seconds) // 60)
    sec = float(seconds) % 60
    return f"{minutes}:{sec:06.3f}"

def find_madrid_session(session_name):
    sessions = pd.DataFrame(
        api_get("sessions", {"year": YEAR})
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

    # Jangan filter hanya country_name=Spain karena 2026 juga ada Barcelona.
    madrid_mask = (
        location.astype(str).str.contains(
            r"Madrid|Madring",
            case=False,
            regex=True,
            na=False
        )
        |
        circuit.astype(str).str.contains(
            r"Madrid|Madring",
            case=False,
            regex=True,
            na=False
        )
    )

    madrid = sessions[madrid_mask].copy()

    if madrid.empty:
        raise RuntimeError(
            "Session Madrid / Madring 2026 tidak ditemukan di OpenF1."
        )

    selected = madrid[
        madrid["session_name"]
        .astype(str)
        .str.lower()
        .eq(session_name.lower())
    ].copy()

    if selected.empty:
        raise RuntimeError(
            f"Session {session_name} Madrid 2026 tidak ditemukan."
        )

    selected["_parsed_start"] = parse_dt(selected["date_start"])

    return (
        selected
        .sort_values("_parsed_start")
        .iloc[-1]
    )

def load_driver_maps(session_key):
    drivers = pd.DataFrame(
        api_get("drivers", {"session_key": int(session_key)})
    )

    drivers["driver_number"] = pd.to_numeric(
        drivers["driver_number"],
        errors="coerce"
    )

    drivers = (
        drivers
        .dropna(subset=["driver_number"])
        .copy()
    )

    drivers["driver_number"] = drivers["driver_number"].astype(int)
    drivers = drivers.drop_duplicates("driver_number")

    acronym = (
        drivers
        .set_index("driver_number")["name_acronym"]
        .to_dict()
    )

    full_name = (
        drivers
        .set_index("driver_number")["full_name"]
        .to_dict()
        if "full_name" in drivers.columns
        else {}
    )

    team = (
        drivers
        .set_index("driver_number")["team_name"]
        .to_dict()
        if "team_name" in drivers.columns
        else {}
    )

    return drivers, acronym, full_name, team


def extract_q3(value):
    if isinstance(value, (list, tuple, np.ndarray)):
        return value[2] if len(value) >= 3 else np.nan
    return np.nan

session = find_madrid_session("Qualifying")
SESSION_KEY = int(session["session_key"])

drivers, driver_map, _, _ = load_driver_maps(SESSION_KEY)

results = pd.DataFrame(
    api_get("session_result", {"session_key": SESSION_KEY})
)

results["position"] = pd.to_numeric(results["position"], errors="coerce")
results["driver_number"] = pd.to_numeric(
    results["driver_number"],
    errors="coerce"
)
results["Q3Seconds"] = results["duration"].apply(extract_q3)

q3_plot = results[
    results["position"].between(1, 10)
    &
    results["Q3Seconds"].notna()
].copy()

q3_plot["driver_number"] = q3_plot["driver_number"].astype(int)
q3_plot["Driver"] = q3_plot["driver_number"].map(driver_map)

q3_plot = q3_plot.sort_values("position").reset_index(drop=True)

q3_plot["Label"] = (
    "P"
    + q3_plot["position"].astype(int).astype(str)
    + " - "
    + q3_plot["Driver"].astype(str)
)

color_map = plt.colormaps["tab10"]
colors = [color_map(i) for i in range(len(q3_plot))]

fig, ax = plt.subplots(figsize=(11, 6))

bars = ax.barh(
    q3_plot["Label"],
    q3_plot["Q3Seconds"],
    color=colors
)

ax.invert_yaxis()

for bar, (_, row) in zip(bars, q3_plot.iterrows()):
    ax.text(
        row["Q3Seconds"] + 0.02,
        bar.get_y() + bar.get_height() / 2,
        format_seconds(row["Q3Seconds"]),
        va="center",
        fontsize=10,
        fontweight="bold"
    )

ax.set_xlabel("Q3 Lap Time (seconds)")
ax.set_ylabel("Driver")
ax.set_title(
    "MADRID GP 2026 — Q3 Qualifying Times P1–P10",
    fontsize=15,
    fontweight="bold"
)
ax.grid(axis="x", linestyle="--", alpha=0.25)

plt.tight_layout()
plt.show()
