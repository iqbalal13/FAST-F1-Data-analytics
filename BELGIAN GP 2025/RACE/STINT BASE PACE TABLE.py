import matplotlib.pyplot as plt
import pandas as pd

# pastikan summary_df sudah ada
df = summary_df.copy()

# formatting angka
df["AvgPace_s"] = df["AvgPace_s"].round(3)
df["TyreDeg_s_per_lap"] = df["TyreDeg_s_per_lap"].round(4)

# kolom yang ditampilkan (lebih fokus)
cols = ["Driver", "Stint", "Laps", "AvgPace_s", "TyreDeg_s_per_lap"]

# ===== LOOP PER COMPOUND =====
for compound in df["Compound"].unique():

    dfx = df[df["Compound"] == compound].sort_values(["Driver", "Stint"])

    if dfx.empty:
        continue

    fig, ax = plt.subplots(figsize=(11, 0.5 * len(dfx) + 2))
    ax.axis("off")

    table = ax.table(
        cellText=dfx[cols].values,
        colLabels=cols,
        loc="center",
        cellLoc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.4)

    # header styling
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#E6E6E6")

    plt.title(
        f"Top 10 – Stint-based Pace & Tyre Degradation\n"
        f"{compound} | Belgian GP 2025",
        fontsize=14,
        pad=20
    )

    plt.tight_layout()

    filename = f"top10_stint_summary_{compound.lower()}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Saved: {filename}")
