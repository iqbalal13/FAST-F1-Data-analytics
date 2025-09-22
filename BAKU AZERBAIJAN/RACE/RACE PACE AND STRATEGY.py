# Pastikan modul-modul ini sudah diimpor
import fastf1 as ff1
import fastf1.plotting
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches # Diperlukan untuk legenda kustom


# API FASTF1
print("Memuat data sesi untuk GP Azerbaijan 2025...")

session_ita_2025 = ff1.get_session(2025, 'Azerbaijan', 'R')
session_ita_2025.load()

print("Data berhasil dimuat!")
# =========================================================

# 1. Setup matplotlib dari FastF1 (PENTING)
# Ini akan otomatis mengatur warna ban yang benar dan format waktu
fastf1.plotting.setup_mpl()

# 2. Membuat objek plot
fig, ax = plt.subplots(figsize=(15, 9))

# 3. Definisikan warna dasar untuk garis setiap pembalap
# PERBAIKAN: Format warna 'RUS' diperbaiki dan koma yang hilang ditambahkan
driver_colors = {
    'VER': 'darkblue',
    'RUS': '#40E0D0',
    'SAI': '#87CEEB',
    'ANT': '#800080',
    'LAW': '#FFF',
    'TSU': 'cyan',
    'NOR': '#FF8700'
}

# 4. Loop untuk setiap pembalap
for driver, color in driver_colors.items():
    # Ambil semua lap untuk pembalap dan bersihkan data
    laps = session_ita_2025.laps.pick_driver(driver).dropna(subset=['LapTime'])

    # Plot garis utama untuk seluruh balapan pembalap
    ax.plot(laps['LapNumber'], laps['LapTime'], color=color, label=driver, zorder=1)

    # Sekarang, kita tambahkan titik-titik berwarna untuk setiap stint ban
    stints = laps['Stint'].unique()
    for stint in stints:
        # Ambil data lap untuk stint ini saja
        laps_stint = laps[laps['Stint'] == stint]

        # Cari tahu kompon ban yang digunakan
        compound = laps_stint['Compound'].iloc[0]

        # Dapatkan warna standar F1 untuk kompon tersebut
        compound_color = fastf1.plotting.COMPOUND_COLORS[compound]

        # Plot titik-titik di atas garis utama
        ax.plot(laps_stint['LapNumber'], laps_stint['LapTime'],
                marker='o', markersize=5, color=compound_color, linestyle='None', zorder=2)

# 5. Membuat Legenda Kustom
# Karena ada 2 jenis info (pembalap & ban), kita perlu buat legenda secara manual

# Legenda untuk pembalap (dari garis utama)
driver_legend = ax.legend(loc='upper left', title='Drivers')
ax.add_artist(driver_legend) # Tambahkan legenda pembalap ke plot

# Legenda untuk ban
legend_patches = []
for compound, color in fastf1.plotting.COMPOUND_COLORS.items():
    if compound in ['SOFT', 'MEDIUM', 'HARD']: # Hanya tampilkan kompon utama
        patch = mpatches.Patch(color=color, label=compound.capitalize())
        legend_patches.append(patch)

ax.legend(handles=legend_patches, loc='upper right', title='Tire Compound')

# 6. Judul dan Label
ax.set_title("Race Pace and Tire Strategy - Baku GP 2025")
ax.set_xlabel("Nomor Lap")
ax.set_ylabel("Waktu Lap")
plt.grid(True, which='both', linestyle='--', linewidth=0.5)

# Tampilkan plot
plt.show()
