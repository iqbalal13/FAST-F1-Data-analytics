# 1. Memuat Sesi Balapan Dutch GP 2025
print("Memuat data sesi untuk Monza GP 2025...")
# Nama event yang benar untuk GP Belanda di FastF1 adalah 'Netherlands'
session_ned = ff1.get_session(2025, 'Monza', 'R')
session_ned.load()
print("Data berhasil dimuat!")

# 2. Analisis dan Visualisasi
# Kita bandingkan pembalap tuan rumah, Verstappen, dengan Norris
laps_ver = session_ned.laps.pick_driver('VER')
laps_nor = session_ned.laps.pick_driver('NOR')
laps_pia = session_ned.laps.pick_driver('PIA')
laps_lec = session_ned.laps.pick_driver('LEC')
laps_rus = session_ned.laps.pick_driver('RUS')


# Praktik terbaik: Selalu bersihkan data dari LapTime yang kosong
laps_ver_clean = laps_ver.dropna(subset=['LapTime'])
laps_nor_clean = laps_nor.dropna(subset=['LapTime'])
laps_pia_clean = laps_pia.dropna(subset=['LapTime'])
laps_lec_clean = laps_lec.dropna(subset=['LapTime'])
laps_rus_clean = laps_rus.dropna(subset=['LapTime'])

# 3. Membuat Grafik
fig, ax = plt.subplots(figsize=(12, 8))

# Plotting data yang sudah bersih
ax.plot(laps_ver_clean['LapNumber'], laps_ver_clean['LapTime'], color='darkblue', label='Verstappen')
ax.plot(laps_nor_clean['LapNumber'], laps_nor_clean['LapTime'], color='#FF8700', label='Norris') # Warna oranye McLaren
ax.plot(laps_pia_clean['LapNumber'], laps_pia_clean['LapTime'], color='#FFB347', label='Piastri')
ax.plot(laps_lec_clean['LapNumber'], laps_lec_clean['LapTime'], color='red', label='Leclerc')
ax.plot(laps_rus_clean['LapNumber'], laps_rus_clean['LapTime'], color='black', label='Russel')

# Judul dan label yang disesuaikan
ax.set_title("Perbandingan Waktu Lap: Verstappen vs Norris - Monza GP 2025")
ax.set_xlabel("Nomor Lap")
ax.set_ylabel("Waktu Lap")
ax.legend()
plt.grid(True, which='both', linestyle='--', linewidth=0.5)

# Menampilkan grafik
plt.show()
