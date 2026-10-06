# ------------------------------------------------------------
# GRAFIK Q3 P1 -> P10
# ------------------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np

# Ambil ulang data Q3 lalu urutkan P1 -> P10
q3_plot = results[results["Q3"].notna()].copy()
q3_plot = q3_plot.sort_values("Position", ascending=True)

# Convert Q3 ke detik
q3_plot["Q3_seconds"] = q3_plot["Q3"].dt.total_seconds()

# Label sumbu Y
q3_plot["Label"] = q3_plot.apply(
    lambda row: f"P{int(row['Position'])} - {row['Abbreviation']}",
    axis=1
)

# Warna beda per pembalap
color_map = plt.cm.get_cmap("tab10", len(q3_plot))
colors = [color_map(i) for i in range(len(q3_plot))]

# Buat figure
plt.figure(figsize=(10, 6))

bars = plt.barh(
    q3_plot["Label"],
    q3_plot["Q3_seconds"],
    color=colors
)

# P1 di atas
plt.gca().invert_yaxis()

# Judul dan label
plt.title("Q3 Qualifying Sepang / Malaysia - P1 to P10")
plt.xlabel("Lap Time (seconds)")
plt.ylabel("Driver")

# Tambahkan teks waktu di ujung bar
for bar, (_, row) in zip(bars, q3_plot.iterrows()):
    plt.text(
        bar.get_width() + 0.03,
        bar.get_y() + bar.get_height() / 2,
        format_time(row["Q3"]),
        va="center",
        fontsize=10
    )

plt.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.show()
