# ============================================================
# F1 2026 BAHRAIN GP IN MALAYSIA - SEPANG
# TOP 10 RACE FINISH GAP
# LOWER BAR = BETTER / FINISHED CLOSER TO WINNER
# GOOGLE COLAB - ONE CELL
# ============================================================

!pip install -q pandas matplotlib numpy

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 1. OFFICIAL TOP 10 RACE RESULT
#
# Gap = seconds behind race winner
# P1 = 0.000
# ============================================================

data = {
    "Position": [
        1, 2, 3, 4, 5,
        6, 7, 8, 9, 10
    ],

    "Driver": [
        "VER",
        "ANT",
        "HAM",
        "LEC",
        "HAD",
        "PIA",
        "LAW",
        "ALO",
        "NOR",
        "LIN"
    ],

    "Name": [
        "Max Verstappen",
        "Kimi Antonelli",
        "Lewis Hamilton",
        "Charles Leclerc",
        "Isack Hadjar",
        "Oscar Piastri",
        "Liam Lawson",
        "Fernando Alonso",
        "Lando Norris",
        "Arvid Lindblad"
    ],

    "Team": [
        "Red Bull Racing",
        "Mercedes",
        "Ferrari",
        "Ferrari",
        "Red Bull Racing",
        "McLaren",
        "Racing Bulls",
        "Aston Martin",
        "McLaren",
        "Racing Bulls"
    ],

    # seconds behind winner
    "GapSeconds": [
        0.000,
        2.307,
        4.919,
        7.258,
        8.571,
        9.454,
        12.753,
        13.372,
        13.993,
        15.928
    ]
}


df = pd.DataFrame(data)


# ============================================================
# 2. DISPLAY TABLE
# ============================================================

print("=" * 75)
print("2026 BAHRAIN GRAND PRIX IN MALAYSIA")
print("SEPANG INTERNATIONAL CIRCUIT")
print("TOP 10 RACE RESULT")
print("=" * 75)

display(df)


# ============================================================
# 3. PRINT RESULT
# ============================================================

print()

for _, row in df.iterrows():

    if row["Position"] == 1:

        gap_text = "WINNER"

    else:

        gap_text = f"+{row['GapSeconds']:.3f}s"


    print(
        f"P{row['Position']:02d} | "
        f"{row['Driver']:<3} | "
        f"{row['Name']:<20} | "
        f"{gap_text}"
    )


# ============================================================
# 4. DRIVER COLORS
# Setiap pembalap beda warna
# ============================================================

cmap = plt.colormaps["tab10"]

colors = [
    cmap(i)
    for i in range(10)
]


# ============================================================
# 5. PLOT
#
# Semakin rendah bar = semakin dekat ke winner
# ============================================================

fig, ax = plt.subplots(
    figsize=(13, 7)
)


bars = ax.bar(
    df["Driver"],
    df["GapSeconds"],
    color=colors,
    width=0.7
)


# ============================================================
# 6. LABEL POSISI + GAP
# ============================================================

for bar, (_, row) in zip(
    bars,
    df.iterrows()
):

    height = bar.get_height()


    if row["Position"] == 1:

        label = (
            "P1\n"
            "WINNER\n"
            "0.000s"
        )

        # supaya label P1 tetap terlihat meskipun bar = 0
        y_position = 0.35


    else:

        label = (
            f"P{int(row['Position'])}\n"
            f"+{row['GapSeconds']:.3f}s"
        )

        y_position = (
            height + 0.25
        )


    ax.text(
        bar.get_x()
        +
        bar.get_width() / 2,

        y_position,

        label,

        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold"
    )


# ============================================================
# 7. TITLE
# ============================================================

ax.set_title(
    "2026 Bahrain GP in Malaysia — Top 10 Race Finish\n"
    "Gap to Winner (Lower = Better)",
    fontsize=16,
    fontweight="bold",
    pad=20
)


ax.set_xlabel(
    "Driver",
    fontsize=12
)


ax.set_ylabel(
    "Seconds Behind Winner",
    fontsize=12
)


# ============================================================
# 8. Y AXIS
#
# P1 paling bawah = 0 sec
# P10 lebih tinggi karena gap lebih besar
# ============================================================

ax.set_ylim(
    0,
    df["GapSeconds"].max() + 3
)


ax.set_yticks(
    np.arange(
        0,
        19,
        2
    )
)


ax.grid(
    axis="y",
    linestyle="--",
    alpha=0.3
)


# ============================================================
# 9. TAMBAH NAMA DRIVER DI BAWAH
# ============================================================

driver_labels = [

    f"P{pos}\n{driver}"

    for pos, driver in zip(
        df["Position"],
        df["Driver"]
    )
]


ax.set_xticks(
    range(
        len(df)
    )
)


ax.set_xticklabels(
    driver_labels,
    fontsize=10
)


# ============================================================
# 10. CLEAN STYLE
# ============================================================

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

plt.show()
