# ================================================================
# FIND UNDERCUT / OVERCUT BATTLES
# IMPROVED VERSION FOR BAKU
# ================================================================

analysis_rows = []

driver_numbers = sorted(TOP10)


for i in range(len(driver_numbers)):

    for j in range(i + 1, len(driver_numbers)):

        driver_a = driver_numbers[i]
        driver_b = driver_numbers[j]

        pits_a = pit[
            pit["driver_number"] == driver_a
        ]

        pits_b = pit[
            pit["driver_number"] == driver_b
        ]

        if pits_a.empty or pits_b.empty:
            continue


        for _, pa in pits_a.iterrows():

            for _, pb in pits_b.iterrows():

                lap_a = int(
                    pa["lap_number"]
                )

                lap_b = int(
                    pb["lap_number"]
                )


                # ------------------------------------------------
                # SAME LAP = skip
                # Tidak ada clear early vs late pitter
                # ------------------------------------------------
                if lap_a == lap_b:
                    continue


                # ------------------------------------------------
                # Hanya pit cycle berdekatan
                # Baku: terutama 30 vs 31
                # ------------------------------------------------
                if abs(lap_a - lap_b) > 2:
                    continue


                # ------------------------------------------------
                # Early / Late pitter
                # ------------------------------------------------
                if lap_a < lap_b:

                    early_driver = driver_a
                    late_driver = driver_b

                    early_pit = lap_a
                    late_pit = lap_b

                    early_stop = pa
                    late_stop = pb

                else:

                    early_driver = driver_b
                    late_driver = driver_a

                    early_pit = lap_b
                    late_pit = lap_a

                    early_stop = pb
                    late_stop = pa


                # ------------------------------------------------
                # Measurement points
                #
                # BEFORE:
                # end of lap before early pitter pits
                #
                # AFTER:
                # one lap after later pitter pits
                # ------------------------------------------------

                pre_lap = early_pit - 1

                post_lap = late_pit + 1


                early_pre = get_gap(
                    early_driver,
                    pre_lap
                )

                late_pre = get_gap(
                    late_driver,
                    pre_lap
                )

                early_post = get_gap(
                    early_driver,
                    post_lap
                )

                late_post = get_gap(
                    late_driver,
                    post_lap
                )


                if any(
                    pd.isna(x)
                    for x in [
                        early_pre,
                        late_pre,
                        early_post,
                        late_post
                    ]
                ):
                    continue


                # ------------------------------------------------
                # Relative gap
                #
                # positive:
                # early pitter was behind
                #
                # negative:
                # early pitter was ahead
                # ------------------------------------------------

                pre_relative = (
                    early_pre
                    -
                    late_pre
                )

                post_relative = (
                    early_post
                    -
                    late_post
                )


                # ------------------------------------------------
                # IMPORTANT:
                # Kita longgarkan battle gap jadi 30s.
                #
                # Baku bisa punya field spread besar.
                # ------------------------------------------------

                if abs(pre_relative) > 30:
                    continue


                # ------------------------------------------------
                # SWING
                #
                # negative = early pitter gained
                # positive = later pitter gained
                # ------------------------------------------------

                swing = (
                    post_relative
                    -
                    pre_relative
                )


                # ------------------------------------------------
                # Classification
                # ------------------------------------------------

                if (
                    pre_relative > 0
                    and
                    post_relative < 0
                ):

                    classification = (
                        "SUCCESSFUL UNDERCUT"
                    )


                elif (
                    pre_relative < 0
                    and
                    post_relative > 0
                ):

                    classification = (
                        "SUCCESSFUL OVERCUT"
                    )


                elif swing < -0.20:

                    classification = (
                        "UNDERCUT GAIN"
                    )


                elif swing > 0.20:

                    classification = (
                        "OVERCUT GAIN"
                    )


                else:

                    classification = (
                        "NEUTRAL"
                    )


                analysis_rows.append({

                    "EarlyDriver":
                        driver_map.get(
                            early_driver,
                            str(early_driver)
                        ),

                    "LateDriver":
                        driver_map.get(
                            late_driver,
                            str(late_driver)
                        ),

                    "EarlyPitLap":
                        early_pit,

                    "LatePitLap":
                        late_pit,

                    "PreLap":
                        pre_lap,

                    "PostLap":
                        post_lap,

                    "PreRelativeGap":
                        pre_relative,

                    "PostRelativeGap":
                        post_relative,

                    "Swing":
                        swing,

                    "Result":
                        classification

                })


# ================================================================
# RESULT DATAFRAME
# ================================================================

analysis = pd.DataFrame(
    analysis_rows
)


if analysis.empty:

    raise RuntimeError(
        "Tidak ada pit-cycle battle yang valid."
    )


analysis = analysis.drop_duplicates(

    subset=[
        "EarlyDriver",
        "LateDriver",
        "EarlyPitLap",
        "LatePitLap"
    ]

)


analysis["GainMagnitude"] = (
    analysis["Swing"].abs()
)


analysis = (
    analysis
    .sort_values(
        "GainMagnitude",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


# ================================================================
# PRETTY TABLE
# ================================================================

table = analysis.copy()


table["Before"] = (
    table["PreRelativeGap"]
    .map(
        lambda x:
        f"{x:+.3f}s"
    )
)


table["After"] = (
    table["PostRelativeGap"]
    .map(
        lambda x:
        f"{x:+.3f}s"
    )
)


table["Net Swing"] = (
    table["Swing"]
    .map(
        lambda x:
        f"{x:+.3f}s"
    )
)


print("\n" + "=" * 110)
print("AZERBAIJAN GP 2026 — UNDERCUT / OVERCUT RESULTS")
print("=" * 110)

print(
    "Negative swing = earlier pitter gained"
)

print(
    "Positive swing = later pitter gained"
)


display(

    table[
        [
            "EarlyDriver",
            "LateDriver",
            "EarlyPitLap",
            "LatePitLap",
            "Before",
            "After",
            "Net Swing",
            "Result"
        ]
    ]

)


# ================================================================
# KEEP MOST RELEVANT BATTLES
#
# Remove tiny/neutral changes from graph
# ================================================================

plot_df = analysis[
    analysis["Swing"].abs() >= 0.20
].copy()


if plot_df.empty:

    plot_df = analysis.copy()


# Top 15 maximum
plot_df = (
    plot_df
    .head(15)
    .copy()
)


# ================================================================
# LABEL
# ================================================================

plot_df["Battle"] = (

    plot_df["EarlyDriver"]

    +

    " L"

    +

    plot_df["EarlyPitLap"]
    .astype(str)

    +

    "  vs  "

    +

    plot_df["LateDriver"]

    +

    " L"

    +

    plot_df["LatePitLap"]
    .astype(str)

)


# reverse so biggest is at top
plot_df = (
    plot_df
    .iloc[::-1]
)


# ================================================================
# COLORS
# ================================================================

colors = [

    "tab:blue"
    if x < 0

    else

    "tab:orange"

    for x in plot_df["Swing"]

]


# ================================================================
# DYNAMIC FIGURE HEIGHT
#
# This fixes huge single bar.
# ================================================================

n_battles = len(
    plot_df
)


fig_height = max(
    4.5,
    n_battles * 0.7 + 2
)


fig, ax = plt.subplots(

    figsize=(
        14,
        fig_height
    )

)


bars = ax.barh(

    plot_df["Battle"],

    plot_df["Swing"],

    color=colors,

    height=0.55

)


# ================================================================
# ZERO LINE
# ================================================================

ax.axvline(

    0,

    color="black",

    linewidth=1.2

)


# ================================================================
# LABEL BAR
# ================================================================

max_abs = max(
    plot_df["Swing"].abs().max(),
    1
)


label_offset = (
    max_abs * 0.025
)


for bar, (_, row) in zip(

    bars,

    plot_df.iterrows()

):

    value = row["Swing"]

    if value < 0:

        x_text = (
            value
            -
            label_offset
        )

        horizontal_alignment = (
            "right"
        )

    else:

        x_text = (
            value
            +
            label_offset
        )

        horizontal_alignment = (
            "left"
        )


    ax.text(

        x_text,

        bar.get_y()
        +
        bar.get_height() / 2,

        f"{value:+.2f}s",

        va="center",

        ha=horizontal_alignment,

        fontsize=9,

        fontweight="bold"

    )


# ================================================================
# RESULT LABEL INSIDE BAR
# ================================================================

for bar, (_, row) in zip(

    bars,

    plot_df.iterrows()

):

    value = row["Swing"]

    # halfway along bar
    text_x = (
        value / 2
    )


    ax.text(

        text_x,

        bar.get_y()
        +
        bar.get_height() / 2,

        row["Result"],

        va="center",

        ha="center",

        fontsize=8,

        color="white",

        fontweight="bold"

    )


# ================================================================
# X LIMITS WITH MARGIN
# ================================================================

xmin = min(
    plot_df["Swing"].min(),
    0
)

xmax = max(
    plot_df["Swing"].max(),
    0
)


margin = max(
    abs(xmin),
    abs(xmax),
    1
) * 0.18


ax.set_xlim(

    xmin - margin,

    xmax + margin

)


# ================================================================
# STYLE
# ================================================================

ax.set_title(

    "AZERBAIJAN GP 2026 — UNDERCUT / OVERCUT PIT-CYCLE SWING\n"
    "← Earlier Pitter Gain | Later Pitter Gain →",

    fontsize=15,

    fontweight="bold",

    pad=15

)


ax.set_xlabel(
    "Relative Gap Swing (seconds)"
)


ax.set_ylabel(
    "Pit Battle"
)


ax.grid(

    axis="x",

    linestyle="--",

    alpha=0.25

)


plt.tight_layout()

plt.show()


# ================================================================
# SUMMARY
# ================================================================

print()
print("=" * 110)
print("STRONGEST UNDERCUT GAINS")
print("=" * 110)


undercut = analysis[
    analysis["Swing"] < -0.20
].copy()


if undercut.empty:

    print(
        "Tidak ada significant undercut gain."
    )

else:

    display(

        undercut[
            [
                "EarlyDriver",
                "LateDriver",
                "EarlyPitLap",
                "LatePitLap",
                "Swing",
                "Result"
            ]
        ]
        .sort_values(
            "Swing"
        )

    )


print()
print("=" * 110)
print("STRONGEST OVERCUT GAINS")
print("=" * 110)


overcut = analysis[
    analysis["Swing"] > 0.20
].copy()


if overcut.empty:

    print(
        "Tidak ada significant overcut gain."
    )

else:

    display(

        overcut[
            [
                "EarlyDriver",
                "LateDriver",
                "EarlyPitLap",
                "LatePitLap",
                "Swing",
                "Result"
            ]
        ]
        .sort_values(
            "Swing",
            ascending=False
        )

    )
