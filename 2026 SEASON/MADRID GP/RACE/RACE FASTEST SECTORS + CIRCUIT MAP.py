# ================================================================
# MADRID GP 2026 — MADRING
# RACE FASTEST SECTORS + CIRCUIT MAP
# OPENF1 — GOOGLE COLAB — ONE CELL
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


from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

print("=" * 78)
print("MADRID GP 2026 — RACE FASTEST SECTORS")
print("=" * 78)

session = find_madrid_session("Race")
SESSION_KEY = int(session["session_key"])

print("Session Key :", SESSION_KEY)
print("Location    :", session.get("location", "Madrid"))
print("Circuit     :", session.get("circuit_short_name", "Madring"))

drivers, driver_map, _, _ = load_driver_maps(SESSION_KEY)

laps = pd.DataFrame(
    api_get("laps", {"session_key": SESSION_KEY})
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
        laps[col] = pd.to_numeric(laps[col], errors="coerce")

if "is_pit_out_lap" in laps.columns:
    race_laps = laps[laps["is_pit_out_lap"] != True].copy()
else:
    race_laps = laps.copy()

race_laps = race_laps.dropna(
    subset=[
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3"
    ]
)

race_laps = race_laps[
    (race_laps["duration_sector_1"] > 0)
    &
    (race_laps["duration_sector_2"] > 0)
    &
    (race_laps["duration_sector_3"] > 0)
].copy()

if race_laps.empty:
    raise RuntimeError("Tidak ada valid race sector data Madrid 2026.")

race_laps["Driver"] = race_laps["driver_number"].map(driver_map)
race_laps["Driver"] = race_laps["Driver"].fillna(
    race_laps["driver_number"].astype(str)
)

sector_columns = {
    "S1": "duration_sector_1",
    "S2": "duration_sector_2",
    "S3": "duration_sector_3"
}

sector_rows = []

for sector_name, col in sector_columns.items():
    idx = race_laps[col].idxmin()
    row = race_laps.loc[idx]

    sector_rows.append({
        "Sector": sector_name,
        "Driver": row["Driver"],
        "DriverNumber": int(row["driver_number"]),
        "Lap": int(row["lap_number"]),
        "Time": float(row[col])
    })

sector_df = pd.DataFrame(sector_rows)

print("\n" + "=" * 78)
print("FASTEST RACE SECTORS")
print("=" * 78)

sector_display = sector_df.copy()
sector_display["Time"] = sector_display["Time"].map(
    lambda x: f"{x:.3f} s"
)
display(sector_display)

complete = race_laps[
    race_laps["lap_duration"].notna()
    &
    (race_laps["lap_duration"] > 0)
].copy()

if complete.empty:
    race_laps["calculated_time"] = (
        race_laps["duration_sector_1"]
        + race_laps["duration_sector_2"]
        + race_laps["duration_sector_3"]
    )
    fastest = race_laps.loc[race_laps["calculated_time"].idxmin()]
    FASTEST_TIME = float(fastest["calculated_time"])
else:
    fastest = complete.loc[complete["lap_duration"].idxmin()]
    FASTEST_TIME = float(fastest["lap_duration"])

FASTEST_DRIVER_NUM = int(fastest["driver_number"])
FASTEST_DRIVER = driver_map.get(
    FASTEST_DRIVER_NUM,
    str(FASTEST_DRIVER_NUM)
)
FASTEST_LAP = int(fastest["lap_number"])

lap_start = parse_dt(fastest["date_start"])
lap_end = lap_start + pd.Timedelta(seconds=FASTEST_TIME)

print("\n" + "=" * 78)
print("FASTEST FULL RACE LAP")
print("=" * 78)
print("Driver:", FASTEST_DRIVER)
print("Lap   :", FASTEST_LAP)
print("Time  :", format_seconds(FASTEST_TIME))

location = pd.DataFrame(
    api_get(
        "location",
        {
            "session_key": SESSION_KEY,
            "driver_number": FASTEST_DRIVER_NUM,
            "date>": (lap_start - pd.Timedelta(seconds=2)).isoformat(),
            "date<": (lap_end + pd.Timedelta(seconds=2)).isoformat()
        }
    )
)

location["date_parsed"] = parse_dt(location["date"])
location["x"] = pd.to_numeric(location["x"], errors="coerce")
location["y"] = pd.to_numeric(location["y"], errors="coerce")

location = (
    location
    .dropna(subset=["date_parsed", "x", "y"])
    .sort_values("date_parsed")
)

location = location[
    ~((location["x"] == 0) & (location["y"] == 0))
].copy()

track = location[
    location["date_parsed"].between(lap_start, lap_end)
].copy()

if len(track) < 20:
    raise RuntimeError(
        f"Location points terlalu sedikit untuk map: {len(track)}"
    )

track["elapsed"] = (
    track["date_parsed"] - lap_start
).dt.total_seconds()

lap_s1 = float(fastest["duration_sector_1"])
lap_s2 = float(fastest["duration_sector_2"])
lap_s3 = float(fastest["duration_sector_3"])

S1_END = lap_s1
S2_END = lap_s1 + lap_s2

x = track["x"].to_numpy(dtype=float)
y = track["y"].to_numpy(dtype=float)
elapsed = track["elapsed"].to_numpy(dtype=float)

valid = np.ones(len(x), dtype=bool)
if len(x) > 1:
    valid[1:] = (np.diff(x) != 0) | (np.diff(y) != 0)

x = x[valid]
y = y[valid]
elapsed = elapsed[valid]

points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)

sector_colors = []

for t in elapsed[:-1]:
    if t <= S1_END:
        sector_colors.append("red")
    elif t <= S2_END:
        sector_colors.append("green")
    else:
        sector_colors.append("blue")

fig, ax = plt.subplots(figsize=(14, 9))

lc = LineCollection(
    segments,
    colors=sector_colors,
    linewidth=7,
    capstyle="round",
    joinstyle="round"
)

ax.add_collection(lc)
ax.set_aspect("equal", adjustable="box")

mx = max((x.max() - x.min()) * 0.08, 100)
my = max((y.max() - y.min()) * 0.08, 100)

ax.set_xlim(x.min() - mx, x.max() + mx)
ax.set_ylim(y.min() - my, y.max() + my)

ax.scatter(
    x[0],
    y[0],
    s=150,
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

s1 = sector_df[sector_df["Sector"] == "S1"].iloc[0]
s2 = sector_df[sector_df["Sector"] == "S2"].iloc[0]
s3 = sector_df[sector_df["Sector"] == "S3"].iloc[0]

ax.set_title(
    "MADRID GP 2026 — RACE FASTEST SECTORS | MADRING\n"
    f"S1: {s1['Driver']} {s1['Time']:.3f}s   |   "
    f"S2: {s2['Driver']} {s2['Time']:.3f}s   |   "
    f"S3: {s3['Driver']} {s3['Time']:.3f}s",
    fontsize=15,
    fontweight="bold",
    pad=18
)

legend_elements = [
    Line2D([0], [0], color="red", lw=7,
           label=f"S1 — {s1['Driver']} {s1['Time']:.3f}s"),
    Line2D([0], [0], color="green", lw=7,
           label=f"S2 — {s2['Driver']} {s2['Time']:.3f}s"),
    Line2D([0], [0], color="blue", lw=7,
           label=f"S3 — {s3['Driver']} {s3['Time']:.3f}s")
]

ax.legend(handles=legend_elements, loc="best", fontsize=10)
ax.axis("off")

plt.tight_layout()
plt.show()
