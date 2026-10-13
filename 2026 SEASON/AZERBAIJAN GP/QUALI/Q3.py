# ============================================================
# F1 2026 AZERBAIJAN / BAKU QUALIFYING Q3
# OUTPUT: TABLE + GRAPH P1 -> P10
# GOOGLE COLAB - ONE CELL
# ============================================================

# Install library
!pip install -q fastf1 pandas matplotlib

# Import
import fastf1
import pandas as pd
import matplotlib.pyplot as plt
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
# Cari event Azerbaijan / Baku otomatis
# ------------------------------------------------------------
schedule = fastf1.get_event_schedule(YEAR)

mask = (
    schedule["Country"].astype(str).str.contains("Azerbaijan", case=False, na=False)
    |
    schedule["Location"].astype(str).str.contains("Baku", case=False, na=False)
)

event = schedule[mask]

if event.empty:
    raise ValueError("Event Azerbaijan / Baku tidak ditemukan.")

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
session = fastf1.get_session(YEAR, ROUND, "Q")
session.load()

# ------------------------------------------------------------
# Ambil hasil Q3
# ------------------------------------------------------------
results = session.results.copy()

q3 = results[results["Q3"].notna()].copy()

# untuk tabel P10 -> P1
q3_desc = q3.sort_values(by="Position", ascending=False).copy()

# untuk grafik P1 -> P10
q3_asc = q3.sort_values(by="Position", ascending=True).copy()

# ------------------------------------------------------------
# Format waktu
# ------------------------------------------------------------
def format_time(td):
    if pd.isna(td):
        return "-"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"

# tabel
q3_desc["Q3_Time"] = q3_desc["Q3"].apply(format_time)

q3_table = q3_desc[
    ["Position", "Abbreviation", "FullName", "TeamName", "Q3_Time"]
].copy()

q3_table["Position"] = q3_table["Position"].astype(int)

q3_table = q3_table.rename(
    columns={
        "Position": "Pos",
        "Abbreviation": "Driver",
        "FullName": "Name",
        "TeamName": "Team",
        "Q3_Time": "Q3 Time"
    }
).reset_index(drop=True)

# ------------------------------------------------------------
# Print tabel P10 -> P1
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
display(q3_table)

# ------------------------------------------------------------
# Siapkan data grafik P1 -> P10
# ------------------------------------------------------------
q3_asc["Position"] = q3_asc["Position"].astype(int)
q3_asc["LapSeconds"] = q3_asc["Q3"].dt.total_seconds()

pole_time = q3_asc["LapSeconds"].min()
q3_asc["DeltaToPole"] = q3_asc["LapSeconds"] - pole_time
q3_asc["Label"] = "P" + q3_asc["Position"].astype(str) + " - " + q3_asc["Abbreviation"]

# ------------------------------------------------------------
# Warna berbeda untuk setiap pembalap
# ------------------------------------------------------------
cmap = plt.colormaps["tab10"]
driver_colors = {
    driver: cmap(i)
    for i, driver in enumerate(q3_asc["Abbreviation"].tolist())
}
colors = [
    driver_colors[driver]
    for driver in q3_asc["Abbreviation"]
]

# ------------------------------------------------------------
# Grafik 1: waktu Q3 absolut
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))
plt.barh(q3_asc["Label"], q3_asc["LapSeconds"], color=colors)
plt.gca().invert_yaxis()

for i, row in q3_asc.reset_index(drop=True).iterrows():
    plt.text(
        row["LapSeconds"] + 0.01,
        i,
        format_time(row["Q3"]),
        va="center"
    )

plt.xlabel("Lap Time (seconds)")
plt.ylabel("Driver")
plt.title("Azerbaijan GP 2026 — Q3 Qualifying Times - P1 to P10")
plt.tight_layout()
plt.show()

# ------------------------------------------------------------
# Grafik 2: gap ke pole
# ------------------------------------------------------------
plt.figure(figsize=(10, 6))
plt.barh(q3_asc["Label"], q3_asc["DeltaToPole"], color=colors)
plt.gca().invert_yaxis()

for i, row in q3_asc.reset_index(drop=True).iterrows():
    if row["DeltaToPole"] == 0:
        text = "POLE"
        x_pos = 0.01
    else:
        text = f"+{row['DeltaToPole']:.3f}s"
        x_pos = row["DeltaToPole"] + 0.005

    plt.text(
        x_pos,
        i,
        text,
        va="center"
    )

plt.xlabel("Gap to Pole (seconds)")
plt.ylabel("Driver")
plt.title("Azerbaijan GP 2026 — Q3 Gap to Pole - P1 to P10")
plt.tight_layout()
plt.show()
