# ------------------------------------------------------------
# WARNA PER PEMBALAP
# ------------------------------------------------------------

# 10 warna berbeda
cmap = plt.colormaps["tab10"]

driver_colors = {
    driver: cmap(i)
    for i, driver in enumerate(q3_asc["Abbreviation"].tolist())
}

# warna sesuai urutan driver di dataframe
colors = [
    driver_colors[driver]
    for driver in q3_asc["Abbreviation"]
]


# ------------------------------------------------------------
# Grafik 1: waktu Q3 absolut
# ------------------------------------------------------------

plt.figure(figsize=(10, 6))

plt.barh(
    q3_asc["Label"],
    q3_asc["LapSeconds"],
    color=colors
)

plt.gca().invert_yaxis()

for i, row in q3_asc.reset_index(drop=True).iterrows():

    plt.text(
        row["LapSeconds"] + 0.01,
        i,
        format_time(row["Q3"]),
        va="center",
        fontsize=10,
        fontweight="bold"
    )

plt.xlabel("Lap Time (seconds)")
plt.ylabel("Driver")

plt.title(
    "Q3 Qualifying Times - P1 to P10",
    fontweight="bold"
)

plt.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)

plt.tight_layout()
plt.show()


# ------------------------------------------------------------
# Grafik 2: gap ke pole
# ------------------------------------------------------------

plt.figure(figsize=(10, 6))

plt.barh(
    q3_asc["Label"],
    q3_asc["DeltaToPole"],
    color=colors
)

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
        va="center",
        fontsize=10,
        fontweight="bold"
    )


plt.xlabel("Gap to Pole (seconds)")
plt.ylabel("Driver")

plt.title(
    "Q3 Gap to Pole - P1 to P10",
    fontweight="bold"
)

plt.grid(
    axis="x",
    linestyle="--",
    alpha=0.25
)

plt.tight_layout()
plt.show()
