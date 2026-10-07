# ================================================================
# SEPANG / KUALA LUMPUR 2026
# RACE FASTEST SECTORS + CIRCUIT MAP
# OPENF1 - GOOGLE COLAB - ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

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


# ================================================================
# API HELPER
# ================================================================

def api_get(endpoint, params=None, allow_empty=False):
    url = f"{BASE}/{endpoint}"

    r = requests.get(
        url,
        params=params,
        timeout=90,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    )

    if r.status_code != 200:
        print("\nAPI ERROR")
        print("URL    :", r.url)
        print("Status :", r.status_code)
        print("Body   :", r.text[:500])
        raise RuntimeError(f"OpenF1 HTTP {r.status_code}")

    data = r.json()

    if not data and not allow_empty:
        raise RuntimeError(f"No data returned from {endpoint}")

    return data


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
# 1. LOAD ALL SESSIONS 2026
# ================================================================

print("=" * 70)
print("LOAD 2026 SESSIONS")
print("=" * 70)

sessions = pd.DataFrame(
    api_get(
        "sessions",
        {"year": YEAR}
    )
)

print("Total 2026 sessions:", len(sessions))


# ================================================================
# 2. CARI SEPANG / KUALA LUMPUR SECARA LOKAL
# ================================================================

location_mask = (
    sessions["location"].astype(str).str.contains(
        "Kuala Lumpur|Sepang",
        case=False,
        regex=True,
        na=False
    )
    |
    sessions["circuit_short_name"].astype(str).str.contains(
        "Sepang|Kuala Lumpur",
        case=False,
        regex=True,
        na=False
    )
)

sepang_sessions = sessions[location_mask].copy()

print("\nMatching sessions:")
display(
    sepang_sessions[
        [
            "session_key",
            "meeting_key",
            "session_name",
            "country_name",
            "location",
            "circuit_short_name",
            "date_start",
            "date_end"
        ]
    ]
)

if sepang_sessions.empty:
    raise RuntimeError(
        "OpenF1 tidak menemukan session Kuala Lumpur / Sepang 2026."
    )


# ================================================================
# 3. PILIH RACE SESSION
# ================================================================

race_sessions = sepang_sessions[
    sepang_sessions["session_name"].astype(str).str.lower().eq("race")
].copy()

if race_sessions.empty:
    raise RuntimeError("Race session Sepang tidak ditemukan.")

race_sessions["parsed_start"] = parse_dt(
    race_sessions["date_start"]
)

race_sessions = race_sessions.sort_values("parsed_start")

session = race_sessions.iloc[-1]

SESSION_KEY = int(session["session_key"])
MEETING_KEY = int(session["meeting_key"])

SESSION_START = parse_dt(session["date_start"])
SESSION_END = parse_dt(session["date_end"])

print("\n" + "=" * 70)
print("RACE SESSION FOUND")
print("=" * 70)
print("Session Key :", SESSION_KEY)
print("Meeting Key :", MEETING_KEY)
print("Location    :", session["location"])
print("Country     :", session["country_name"])
print("Circuit     :", session["circuit_short_name"])
print("Start       :", SESSION_START)
print("End         :", SESSION_END)


# ================================================================
# 4. DRIVER DATA
# ================================================================

drivers = pd.DataFrame(
    api_get(
        "drivers",
        {"session_key": SESSION_KEY}
    )
)

drivers = drivers.drop_duplicates("driver_number")

driver_map = (
    drivers
    .set_index("driver_number")["name_acronym"]
    .to_dict()
)


# ================================================================
# 5. LOAD LAP DATA
# ================================================================

print("\n" + "=" * 70)
print("LOAD RACE LAP DATA")
print("=" * 70)

laps = pd.DataFrame(
    api_get(
        "laps",
        {"session_key": SESSION_KEY}
    )
)

if laps.empty:
    raise RuntimeError("Lap data race kosong.")

laps["date_parsed"] = parse_dt(laps["date_start"])

numeric_columns = [
    "driver_number",
    "lap_number",
    "lap_duration",
    "duration_sector_1",
    "duration_sector_2",
    "duration_sector_3"
]

for column in numeric_columns:
    if column in laps.columns:
        laps[column] = pd.to_numeric(
            laps[column],
            errors="coerce"
        )

# buang row yang tanggalnya invalid
laps = laps[laps["date_parsed"].notna()].copy()

print("Total race laps:", len(laps))


# ================================================================
# 6. FILTER VALID TIMED LAPS
# ================================================================

race_laps = laps.copy()

# buang pit-out kalau ada
if "is_pit_out_lap" in race_laps.columns:
    race_laps = race_laps[race_laps["is_pit_out_lap"] != True].copy()

# wajib punya sector lengkap
race_laps = race_laps.dropna(
    subset=[
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3"
    ]
)

# sector valid
race_laps = race_laps[
    (race_laps["duration_sector_1"] > 0)
    &
    (race_laps["duration_sector_2"] > 0)
    &
    (race_laps["duration_sector_3"] > 0)
].copy()

if race_laps.empty:
    raise RuntimeError("Tidak ada valid timed laps untuk race.")

race_laps["Driver"] = race_laps["driver_number"].map(driver_map)
race_laps["Driver"] = race_laps["Driver"].fillna(
    race_laps["driver_number"].astype(str)
)

print("Valid race timed laps:", len(race_laps))
print("Drivers:", sorted(race_laps["Driver"].unique()))


# ================================================================
# 7. FASTEST INDIVIDUAL SECTORS SEPANJANG RACE
# ================================================================

sector_columns = {
    "S1": "duration_sector_1",
    "S2": "duration_sector_2",
    "S3": "duration_sector_3"
}

sector_results = []

for sector, column in sector_columns.items():
    idx = race_laps[column].idxmin()
    row = race_laps.loc[idx]

    sector_results.append({
        "Sector": sector,
        "Driver": row["Driver"],
        "DriverNumber": int(row["driver_number"]),
        "Lap": int(row["lap_number"]),
        "Time": float(row[column])
    })

sector_df = pd.DataFrame(sector_results)

print("\n" + "=" * 70)
print("FASTEST RACE SECTORS")
print("=" * 70)

sector_table = sector_df.copy()
sector_table["Time"] = sector_table["Time"].map(
    lambda x: f"{x:.3f} s"
)

display(sector_table)

print()
for _, row in sector_df.iterrows():
    print(
        f"{row['Sector']}  |  "
        f"{row['Driver']:<4}  |  "
        f"{row['Time']:.3f} s  |  "
        f"Lap {int(row['Lap'])}"
    )


# ================================================================
# 8. FASTEST FULL RACE LAP
#
# Ini dipakai sebagai base untuk map circuit
# ================================================================

complete = race_laps[race_laps["lap_duration"].notna()].copy()
complete = complete[complete["lap_duration"] > 0]

if complete.empty:
    race_laps["calculated_time"] = (
        race_laps["duration_sector_1"]
        + race_laps["duration_sector_2"]
        + race_laps["duration_sector_3"]
    )

    fastest = race_laps.loc[
        race_laps["calculated_time"].idxmin()
    ]

    FASTEST_TIME = float(fastest["calculated_time"])
else:
    fastest = complete.loc[
        complete["lap_duration"].idxmin()
    ]

    FASTEST_TIME = float(fastest["lap_duration"])

FASTEST_DRIVER_NUM = int(fastest["driver_number"])
FASTEST_DRIVER = driver_map.get(
    FASTEST_DRIVER_NUM,
    str(FASTEST_DRIVER_NUM)
)
FASTEST_LAP = int(fastest["lap_number"])

print("\n" + "=" * 70)
print("FASTEST FULL RACE LAP")
print("=" * 70)
print("Driver:", FASTEST_DRIVER)
print("Lap   :", FASTEST_LAP)
print("Time  :", f"{FASTEST_TIME:.3f} s")


# ================================================================
# 9. LAP START / END
# ================================================================

lap_start = parse_dt(fastest["date_start"])

if pd.isna(lap_start):
    raise RuntimeError("Tanggal fastest lap tidak bisa diparse.")

lap_end = lap_start + pd.Timedelta(seconds=FASTEST_TIME)


# ================================================================
# 10. LOAD LOCATION DATA UNTUK FASTEST DRIVER
# ================================================================

print("\n" + "=" * 70)
print("LOAD TRACK LOCATION DATA")
print("=" * 70)

location = pd.DataFrame(
    api_get(
        "location",
        {
            "session_key": SESSION_KEY,
            "driver_number": FASTEST_DRIVER_NUM
        }
    )
)

if location.empty:
    raise RuntimeError("Location data kosong.")

location["date_parsed"] = parse_dt(location["date"])
location["x"] = pd.to_numeric(location["x"], errors="coerce")
location["y"] = pd.to_numeric(location["y"], errors="coerce")

location = location.dropna(
    subset=["date_parsed", "x", "y"]
).copy()

# buang titik invalid
location = location[
    ~((location["x"] == 0) & (location["y"] == 0))
].copy()

location = location.sort_values("date_parsed")


# ================================================================
# 11. FILTER HANYA FASTEST LAP
# ================================================================

track = location[
    (location["date_parsed"] >= lap_start)
    &
    (location["date_parsed"] <= lap_end)
].copy()

if len(track) < 20:
    raise RuntimeError(
        f"Location points terlalu sedikit: {len(track)}"
    )

track["elapsed"] = (
    track["date_parsed"] - lap_start
).dt.total_seconds()


# ================================================================
# 12. BOUNDARY SECTOR PADA FASTEST RACE LAP
# ================================================================

lap_s1 = float(fastest["duration_sector_1"])
lap_s2 = float(fastest["duration_sector_2"])
lap_s3 = float(fastest["duration_sector_3"])

S1_END = lap_s1
S2_END = lap_s1 + lap_s2


# ================================================================
# 13. XY DATA
# ================================================================

x = track["x"].to_numpy(dtype=float)
y = track["y"].to_numpy(dtype=float)
t = track["elapsed"].to_numpy(dtype=float)

points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)


# ================================================================
# 14. WARNA SECTOR
# ================================================================

colors = []

for sec in t[:-1]:
    if sec <= S1_END:
        colors.append("red")
    elif sec <= S2_END:
        colors.append("green")
    else:
        colors.append("blue")


# ================================================================
# 15. PLOT CIRCUIT MAP
# ================================================================

fig, ax = plt.subplots(figsize=(12, 9))

lc = LineCollection(
    segments,
    colors=colors,
    linewidth=7,
    capstyle="round",
    joinstyle="round"
)

ax.add_collection(lc)

ax.set_aspect("equal", adjustable="box")

mx = (x.max() - x.min()) * 0.08
my = (y.max() - y.min()) * 0.08

ax.set_xlim(x.min() - mx, x.max() + mx)
ax.set_ylim(y.min() - my, y.max() + my)


# ================================================================
# 16. START / FINISH
# ================================================================

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


# ================================================================
# 17. TITLE + LEGEND DATA
# ================================================================

s1 = sector_df[sector_df["Sector"] == "S1"].iloc[0]
s2 = sector_df[sector_df["Sector"] == "S2"].iloc[0]
s3 = sector_df[sector_df["Sector"] == "S3"].iloc[0]

ax.set_title(
    "SEPANG 2026 — RACE FASTEST SECTORS\n"
    f"S1: {s1['Driver']} {s1['Time']:.3f}s   |   "
    f"S2: {s2['Driver']} {s2['Time']:.3f}s   |   "
    f"S3: {s3['Driver']} {s3['Time']:.3f}s",
    fontsize=15,
    fontweight="bold",
    pad=20
)

legend = [
    Line2D(
        [0], [0],
        color="red",
        lw=7,
        label=f"S1 — {s1['Driver']} {s1['Time']:.3f}s"
    ),
    Line2D(
        [0], [0],
        color="green",
        lw=7,
        label=f"S2 — {s2['Driver']} {s2['Time']:.3f}s"
    ),
    Line2D(
        [0], [0],
        color="blue",
        lw=7,
        label=f"S3 — {s3['Driver']} {s3['Time']:.3f}s"
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

ax.legend(handles=legend, loc="best")
ax.axis("off")

plt.tight_layout()
plt.show()
