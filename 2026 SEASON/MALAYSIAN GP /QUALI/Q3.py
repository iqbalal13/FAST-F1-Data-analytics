# ============================================================
# F1 2026 MALAYSIA / SEPANG QUALIFYING Q3
# OUTPUT: P10 -> P1
# GOOGLE COLAB - ONE CELL
# ============================================================

# Install library
!pip install -q fastf1 pandas

# Import
import fastf1
import pandas as pd
import os

# ------------------------------------------------------------
# FastF1 Cache
# ------------------------------------------------------------
CACHE_DIR = "/content/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

fastf1.Cache.enable_cache(CACHE_DIR)

# ------------------------------------------------------------
# Setting
# ------------------------------------------------------------
YEAR = 2026

# ------------------------------------------------------------
# Cari event Malaysia / Sepang otomatis
# ------------------------------------------------------------
schedule = fastf1.get_event_schedule(YEAR)

mask = (
    schedule["Country"].astype(str).str.contains(
        "Malaysia",
        case=False,
        na=False
    )
    |
    schedule["Location"].astype(str).str.contains(
        "Sepang",
        case=False,
        na=False
    )
    |
    schedule["Location"].astype(str).str.contains(
        "Kuala Lumpur",
        case=False,
        na=False
    )
)

event = schedule[mask]

if event.empty:
    raise ValueError("Event Malaysia / Sepang tidak ditemukan.")

ROUND = int(event.iloc[0]["RoundNumber"])

print("==============================================")
print("EVENT FOUND")
print("==============================================")
print("Year     :", YEAR)
print("Round    :", ROUND)
print("Event    :", event.iloc[0]["EventName"])
print("Country  :", event.iloc[0]["Country"])
print("Location :", event.iloc[0]["Location"])
print()

# ------------------------------------------------------------
# Load Qualifying
# ------------------------------------------------------------
session = fastf1.get_session(
    YEAR,
    ROUND,
    "Q"
)

session.load()

# ------------------------------------------------------------
# Ambil hasil qualifying
# ------------------------------------------------------------
results = session.results.copy()

# Hanya driver yang masuk Q3
q3 = results[
    results["Q3"].notna()
].copy()

# Position ascending=False:
# P10 -> P1
q3 = q3.sort_values(
    by="Position",
    ascending=False
)

# ------------------------------------------------------------
# Format lap time
# ------------------------------------------------------------
def format_time(td):
    if pd.isna(td):
        return "-"

    total_seconds = td.total_seconds()

    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:06.3f}"

q3["Q3_Time"] = q3["Q3"].apply(format_time)

# ------------------------------------------------------------
# Buat tabel
# ------------------------------------------------------------
q3_table = q3[
    [
        "Position",
        "Abbreviation",
        "FullName",
        "TeamName",
        "Q3_Time"
    ]
].copy()

q3_table["Position"] = (
    q3_table["Position"]
    .astype(int)
)

q3_table = q3_table.rename(
    columns={
        "Position": "Pos",
        "Abbreviation": "Driver",
        "FullName": "Name",
        "TeamName": "Team",
        "Q3_Time": "Q3 Time"
    }
)

q3_table = q3_table.reset_index(drop=True)

# ------------------------------------------------------------
# Print P10 -> P1
# ------------------------------------------------------------
print("==============================================")
print("Q3 RESULT - P10 -> P1")
print("==============================================")

for _, row in q3_table.iterrows():

    print(
        f"P{row['Pos']:02d} | "
        f"{row['Driver']:<3} | "
        f"{row['Name']:<22} | "
        f"{row['Team']:<25} | "
        f"{row['Q3 Time']}"
    )

print("==============================================")

# Tampilkan juga sebagai DataFrame
display(q3_table)# ============================================================
# F1 2026 MALAYSIA / SEPANG QUALIFYING Q3
# OUTPUT: P10 -> P1
# GOOGLE COLAB - ONE CELL
# ============================================================

# Install library
!pip install -q fastf1 pandas

# Import
import fastf1
import pandas as pd
import os

# ------------------------------------------------------------
# FastF1 Cache
# ------------------------------------------------------------
CACHE_DIR = "/content/fastf1_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

fastf1.Cache.enable_cache(CACHE_DIR)

# ------------------------------------------------------------
# Setting
# ------------------------------------------------------------
YEAR = 2026

# ------------------------------------------------------------
# Cari event Malaysia / Sepang otomatis
# ------------------------------------------------------------
schedule = fastf1.get_event_schedule(YEAR)

mask = (
    schedule["Country"].astype(str).str.contains(
        "Malaysia",
        case=False,
        na=False
    )
    |
    schedule["Location"].astype(str).str.contains(
        "Sepang",
        case=False,
        na=False
    )
    |
    schedule["Location"].astype(str).str.contains(
        "Kuala Lumpur",
        case=False,
        na=False
    )
)

event = schedule[mask]

if event.empty:
    raise ValueError("Event Malaysia / Sepang tidak ditemukan.")

ROUND = int(event.iloc[0]["RoundNumber"])

print("==============================================")
print("EVENT FOUND")
print("==============================================")
print("Year     :", YEAR)
print("Round    :", ROUND)
print("Event    :", event.iloc[0]["EventName"])
print("Country  :", event.iloc[0]["Country"])
print("Location :", event.iloc[0]["Location"])
print()

# ------------------------------------------------------------
# Load Qualifying
# ------------------------------------------------------------
session = fastf1.get_session(
    YEAR,
    ROUND,
    "Q"
)

session.load()

# ------------------------------------------------------------
# Ambil hasil qualifying
# ------------------------------------------------------------
results = session.results.copy()

# Hanya driver yang masuk Q3
q3 = results[
    results["Q3"].notna()
].copy()

# Position ascending=False:
# P10 -> P1
q3 = q3.sort_values(
    by="Position",
    ascending=False
)

# ------------------------------------------------------------
# Format lap time
# ------------------------------------------------------------
def format_time(td):
    if pd.isna(td):
        return "-"

    total_seconds = td.total_seconds()

    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:06.3f}"

q3["Q3_Time"] = q3["Q3"].apply(format_time)

# ------------------------------------------------------------
# Buat tabel
# ------------------------------------------------------------
q3_table = q3[
    [
        "Position",
        "Abbreviation",
        "FullName",
        "TeamName",
        "Q3_Time"
    ]
].copy()

q3_table["Position"] = (
    q3_table["Position"]
    .astype(int)
)

q3_table = q3_table.rename(
    columns={
        "Position": "Pos",
        "Abbreviation": "Driver",
        "FullName": "Name",
        "TeamName": "Team",
        "Q3_Time": "Q3 Time"
    }
)

q3_table = q3_table.reset_index(drop=True)

# ------------------------------------------------------------
# Print P10 -> P1
# ------------------------------------------------------------
print("==============================================")
print("Q3 RESULT - P10 -> P1")
print("==============================================")

for _, row in q3_table.iterrows():

    print(
        f"P{row['Pos']:02d} | "
        f"{row['Driver']:<3} | "
        f"{row['Name']:<22} | "
        f"{row['Team']:<25} | "
        f"{row['Q3 Time']}"
    )

print("==============================================")

# Tampilkan juga sebagai DataFrame
display(q3_table)
