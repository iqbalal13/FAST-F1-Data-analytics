import fastf1
import pandas as pd

# Mengatur agar Pandas menampilkan semua kolom
pd.set_option('display.max_columns', None)

# --- LANGKAH 1: AKTIFKAN CACHE ---
# Ini akan mempercepat proses jika skrip dijalankan lagi
try:
    fastf1.Cache.enable_cache('cache')
    print("Cache diaktifkan.")
except Exception as e:
    print(f"Gagal mengaktifkan cache: {e}")

# --- LANGKAH 2: MUAT SESI KUALIFIKASI ---
try:
    print("Memuat data sesi kualifikasi Monza 2025...")
    session = fastf1.get_session(2025, 'Italian Grand Prix', 'Q')
    session.load() # Load semua data lap
    print("Data berhasil dimuat.")
except Exception as e:
    print(f"Gagal memuat sesi. Error: {e}")
    exit()

# --- LANGKAH 3: DAPATKAN LAP TERCEPAT DARI PEMBALAP Q3 ---
# Ambil daftar pembalap yang lolos ke Q3
q3_drivers_abbr = session.results.dropna(subset=['Q3'])['Abbreviation'].tolist()

# Filter semua lap hanya untuk pembalap Q3
laps_q3_drivers = session.laps[session.laps['Driver'].isin(q3_drivers_abbr)]

# Cari lap tercepat untuk setiap pembalap dari daftar tersebut
fastest_laps = laps_q3_drivers.groupby('Driver')['LapTime'].idxmin()
q3_fastest_data = laps_q3_drivers.loc[fastest_laps]

# --- LANGKAH 4: PILIH KOLOM & TAMPILKAN HASIL ---
# Pilih kolom yang relevan: Nama, Tim, Waktu Lap, dan waktu per sektor
columns_to_show = ['Driver', 'Team', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']
final_results = q3_fastest_data[columns_to_show]

# Urutkan berdasarkan waktu lap tercepat
final_results_sorted = final_results.sort_values(by='LapTime').reset_index(drop=True)

print("\n" + "="*80)
print("     Data Lap Tercepat per Sektor Kualifikasi 3 (Q3) - GP Italia 2025     ")
print("="*80)
print(final_results_sorted)
print("="*80)

# --- LANGKAH 5 (BONUS): TEMUKAN PEMBALAP TERCEPAT DI SETIAP SEKTOR ---
fastest_s1_driver = final_results_sorted.loc[final_results_sorted['Sector1Time'].idxmin()]
fastest_s2_driver = final_results_sorted.loc[final_results_sorted['Sector2Time'].idxmin()]
fastest_s3_driver = final_results_sorted.loc[final_results_sorted['Sector3Time'].idxmin()]

print("\nAnalisis Sektor Tercepat (dari lap terbaik pembalap Q3):")
print(f"🚀 Sektor 1 Tercepat: {fastest_s1_driver['Driver']} - {fastest_s1_driver['Sector1Time']}")
print(f"🚀 Sektor 2 Tercepat: {fastest_s2_driver['Driver']} - {fastest_s2_driver['Sector2Time']}")
print(f"🚀 Sektor 3 Tercepat: {fastest_s3_driver['Driver']} - {fastest_s3_driver['Sector3Time']}")
print("\nSkrip selesai.")
