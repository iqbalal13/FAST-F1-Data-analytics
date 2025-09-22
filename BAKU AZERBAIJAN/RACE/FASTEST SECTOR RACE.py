import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib import cm
import numpy as np

# --- LANGKAH 1: PERSIAPAN DAN MEMUAT DATA ---

# Mengaktifkan cache FastF1
try:
    fastf1.Cache.enable_cache('cache')
    print("Cache diaktifkan.")
except Exception as e:
    print(f"Gagal mengaktifkan cache: {e}")

# Setup plotting FastF1
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# Memuat sesi balapan (Race)
try:
    print("Memuat data sesi Azerbaijan 2025...")
    session = fastf1.get_session(2025, 'Azerbaijan Grand Prix', 'R')
    session.load()
    print("Data berhasil dimuat.")
except Exception as e:
    print(f"Gagal memuat sesi. Error: {e}")
    exit()

# --- LANGKAH 2: MENENTUKAN PEMBALAP TERCEPAT PER SEKTOR ---

Race_drivers_abbr = session.results['Abbreviation'].tolist()
laps_Race_drivers = session.laps[session.laps['Driver'].isin(Race_drivers_abbr)]
laps_Race_drivers = laps_Race_drivers.dropna(subset=['LapTime'])
fastest_laps_per_driver = laps_Race_drivers.loc[laps_Race_drivers.groupby('Driver')['LapTime'].idxmin()]

fastest_s1 = fastest_laps_per_driver.loc[fastest_laps_per_driver['Sector1Time'].idxmin()]
fastest_s2 = fastest_laps_per_driver.loc[fastest_laps_per_driver['Sector2Time'].idxmin()]
fastest_s3 = fastest_laps_per_driver.loc[fastest_laps_per_driver['Sector3Time'].idxmin()]

s1_driver = fastest_s1['Driver']
s2_driver = fastest_s2['Driver']
s3_driver = fastest_s3['Driver']

s1_color = fastf1.plotting.team_color(fastest_s1['Team'])
s2_color = fastf1.plotting.team_color(fastest_s2['Team'])
s3_color = fastf1.plotting.team_color(fastest_s3['Team'])

print(f"\nAnalisis Sektor Tercepat:")
print(f"Sektor 1: {s1_driver} ({fastest_s1['Sector1Time'].total_seconds():.3f}s)")
print(f"Sektor 2: {s2_driver} ({fastest_s2['Sector2Time'].total_seconds():.3f}s)")
print(f"Sektor 3: {s3_driver} ({fastest_s3['Sector3Time'].total_seconds():.3f}s)")

# --- LANGKAH 3: MEMBUAT VISUALISASI DI PETA SIRKUIT ---

print("\nMembuat visualisasi...")
race_lap = session.laps.pick_fastest()
pos_data = race_lap.get_telemetry()

s1_end_dist = pos_data.loc[pos_data['SessionTime'] >= race_lap['Sector1SessionTime']].iloc[0]['Distance']
s2_end_dist = pos_data.loc[pos_data['SessionTime'] >= race_lap['Sector2SessionTime']].iloc[0]['Distance']

fig, ax = plt.subplots(figsize=(12, 12))

ax.plot(pos_data[pos_data['Distance'] <= s1_end_dist]['X'], pos_data[pos_data['Distance'] <= s1_end_dist]['Y'],
        color=s1_color, linewidth=5, label=f'Sektor 1 - {s1_driver}')
ax.plot(pos_data[(pos_data['Distance'] > s1_end_dist) & (pos_data['Distance'] <= s2_end_dist)]['X'],
        pos_data[(pos_data['Distance'] > s1_end_dist) & (pos_data['Distance'] <= s2_end_dist)]['Y'],
        color=s2_color, linewidth=5, label=f'Sektor 2 - {s2_driver}')
ax.plot(pos_data[pos_data['Distance'] > s2_end_dist]['X'], pos_data[pos_data['Distance'] > s2_end_dist]['Y'],
        color=s3_color, linewidth=5, label=f'Sektor 3 - {s3_driver}')

ax.set_aspect('equal', 'box')
ax.axis('off')

# ===================================================================
# >> PERBAIKAN FINAL DI SINI <<
# Menggunakan session.name yang lebih andal untuk nama sesi
# ===================================================================
plt.suptitle(f"Pembalap Tercepat per Sektor\n{session.event['EventName']} {session.event.year} {session.name}", fontsize=18)
plt.legend(loc='upper right', fontsize='medium')

plt.show()

print("Visualisasi selesai ditampilkan.")
