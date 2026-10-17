# ================================================================
# MADRID GP 2026 — MADRING
# TOP 10 TYRE DEGRADATION + AVERAGE PACE PER STINT
# OPENF1 — GOOGLE COLAB — ONE CELL
#
# Observed degradation proxy:
# slope lap time vs tyre age (seconds/lap)
# ================================================================

!pip install -q requests pandas numpy matplotlib


import time
import random
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

YEAR = 2026
BASE = "https://api.openf1.org/v1"

LAST_REQUEST_TIME = time.time()
MIN_REQUEST_INTERVAL = 1.10

http = requests.Session()
http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})

def api_get(endpoint, params=None, allow_empty=False, max_retries=10):
    global LAST_REQUEST_TIME

    url = f"{BASE}/{endpoint}"

    for attempt in range(max_retries):
        elapsed = time.time() - LAST_REQUEST_TIME
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        try:
            r = http.get(url, params=params, timeout=90)
            LAST_REQUEST_TIME = time.time()
        except requests.RequestException as e:
            wait = min(3 + attempt * 3, 30)
            print(f"\nNetwork error [{endpoint}]: {e}")
            print(f"Retry dalam {wait}s...")
            time.sleep(wait)
            continue

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = float(retry_after)
                except Exception:
                    wait = min(4 + attempt * 4, 40)
            else:
                wait = min(4 + attempt * 4, 40)

            wait += random.uniform(0.3, 1.0)
            print(f"\n⚠️ OpenF1 rate limit 429 pada {endpoint}.")
            print(f"Retry {attempt + 1}/{max_retries} dalam {wait:.1f}s...")
            time.sleep(wait)
            continue

        if r.status_code != 200:
            print("\nOPENF1 API ERROR")
            print("URL    :", r.url)
            print("Status :", r.status_code)
            print("Body   :", r.text[:500])
            raise RuntimeError(f"OpenF1 HTTP {r.status_code}")

        data = r.json()
        if not data and not allow_empty:
            raise RuntimeError(f"No data returned from {endpoint}")

        return data

    raise RuntimeError(
        f"OpenF1 gagal setelah {max_retries} retry pada endpoint {endpoint}"
    )

def parse_dt(x):
    return pd.to_datetime(
        x,
        format="mixed",
        utc=True,
        errors="coerce"
    )

def format_seconds(seconds):
    if pd.isna(seconds):
        return "-"
    minutes = int(float(seconds) // 60)
    sec = float(seconds) % 60
    return f"{minutes}:{sec:06.3f}"

def find_madrid_session(session_name):
    sessions = pd.DataFrame(
        api_get("sessions", {"year": YEAR})
    )

    location = (
        sessions["location"]
        if "location" in sessions.columns
        else pd.Series("", index=sessions.index)
    )

    circuit = (
        sessions["circuit_short_name"]
        if "circuit_short_name" in sessions.columns
        else pd.Series("", index=sessions.index)
    )

    # Jangan filter hanya country_name=Spain karena 2026 juga ada Barcelona.
    madrid_mask = (
        location.astype(str).str.contains(
            r"Madrid|Madring",
            case=False,
            regex=True,
            na=False
        )
        |
        circuit.astype(str).str.contains(
            r"Madrid|Madring",
            case=False,
            regex=True,
            na=False
        )
    )

    madrid = sessions[madrid_mask].copy()

    if madrid.empty:
        raise RuntimeError(
            "Session Madrid / Madring 2026 tidak ditemukan di OpenF1."
        )

    selected = madrid[
        madrid["session_name"]
        .astype(str)
        .str.lower()
        .eq(session_name.lower())
    ].copy()

    if selected.empty:
        raise RuntimeError(
            f"Session {session_name} Madrid 2026 tidak ditemukan."
        )

    selected["_parsed_start"] = parse_dt(selected["date_start"])

    return (
        selected
        .sort_values("_parsed_start")
        .iloc[-1]
    )

def load_driver_maps(session_key):
    drivers = pd.DataFrame(
        api_get("drivers", {"session_key": int(session_key)})
    )

    drivers["driver_number"] = pd.to_numeric(
        drivers["driver_number"],
        errors="coerce"
    )

    drivers = (
        drivers
        .dropna(subset=["driver_number"])
        .copy()
    )

    drivers["driver_number"] = drivers["driver_number"].astype(int)
    drivers = drivers.drop_duplicates("driver_number")

    acronym = (
        drivers
        .set_index("driver_number")["name_acronym"]
        .to_dict()
    )

    full_name = (
        drivers
        .set_index("driver_number")["full_name"]
        .to_dict()
        if "full_name" in drivers.columns
        else {}
    )

    team = (
        drivers
        .set_index("driver_number")["team_name"]
        .to_dict()
        if "team_name" in drivers.columns
        else {}
    )

    return drivers, acronym, full_name, team


print("=" * 84)
print("MADRID GP 2026 — TYRE DEGRADATION + STINT PACE")
print("=" * 84)

session = find_madrid_session("Race")
SESSION_KEY = int(session["session_key"])

print("Session Key :", SESSION_KEY)
print("Location    :", session.get("location", "Madrid"))
print("Circuit     :", session.get("circuit_short_name", "Madring"))

drivers, driver_map, _, _ = load_driver_maps(SESSION_KEY)

results = pd.DataFrame(
    api_get("session_result", {"session_key": SESSION_KEY})
)

results["position"] = pd.to_numeric(results["position"], errors="coerce")
results["driver_number"] = pd.to_numeric(
    results["driver_number"],
    errors="coerce"
)

top10 = results[
    results["position"].between(1, 10)
].copy()

top10 = top10.sort_values("position").reset_index(drop=True)
top10["driver_number"] = top10["driver_number"].astype(int)
top10["Driver"] = top10["driver_number"].map(driver_map)
top10["Driver"] = top10["Driver"].fillna(
    top10["driver_number"].astype(str)
)

TOP10 = top10["driver_number"].tolist()

print("\nTOP 10:")
display(top10[["position", "Driver", "driver_number"]])

laps = pd.DataFrame(
    api_get("laps", {"session_key": SESSION_KEY})
)

for col in ["driver_number", "lap_number", "lap_duration"]:
    if col in laps.columns:
        laps[col] = pd.to_numeric(laps[col], errors="coerce")

laps = laps[
    laps["driver_number"].isin(TOP10)
].copy()

laps = laps.dropna(
    subset=["driver_number", "lap_number", "lap_duration"]
)

laps = laps[laps["lap_duration"] > 0].copy()

stints = pd.DataFrame(
    api_get("stints", {"session_key": SESSION_KEY})
)

for col in [
    "driver_number",
    "stint_number",
    "lap_start",
    "lap_end",
    "tyre_age_at_start"
]:
    if col in stints.columns:
        stints[col] = pd.to_numeric(
            stints[col],
            errors="coerce"
        )

if "tyre_age_at_start" not in stints.columns:
    stints["tyre_age_at_start"] = 0

stints["tyre_age_at_start"] = (
    stints["tyre_age_at_start"]
    .fillna(0)
)

if "compound" not in stints.columns:
    stints["compound"] = "UNKNOWN"

stints = stints[
    stints["driver_number"].isin(TOP10)
].copy()

stints = stints.dropna(
    subset=["driver_number", "lap_start", "lap_end"]
)

compound_colors = {
    "SOFT": "red",
    "MEDIUM": "gold",
    "HARD": "lightgray",
    "INTERMEDIATE": "green",
    "WET": "blue",
    "UNKNOWN": "black"
}

line_styles = ["-", "--", "-.", ":"]

clean_frames = []
summary_rows = []

for _, result_row in top10.iterrows():
    driver_num = int(result_row["driver_number"])
    driver = result_row["Driver"]
    finish_position = int(result_row["position"])

    ds = stints[
        stints["driver_number"].eq(driver_num)
    ].copy()

    if "stint_number" in ds.columns:
        ds = ds.sort_values("stint_number")
    else:
        ds = ds.sort_values("lap_start")

    ds = ds.reset_index(drop=True)

    if ds.empty:
        continue

    n_stints = len(ds)

    for stint_idx, stint in ds.iterrows():
        lap_start = int(stint["lap_start"])
        lap_end = int(stint["lap_end"])

        stint_number = (
            int(stint["stint_number"])
            if "stint_number" in stint.index
            and pd.notna(stint["stint_number"])
            else stint_idx + 1
        )

        compound = str(
            stint.get("compound", "UNKNOWN")
        ).upper()

        if compound in ("NAN", "NONE", ""):
            compound = "UNKNOWN"

        tyre_age_start = float(
            stint.get("tyre_age_at_start", 0)
        )

        if pd.isna(tyre_age_start):
            tyre_age_start = 0.0

        s = laps[
            laps["driver_number"].eq(driver_num)
            &
            laps["lap_number"].between(lap_start, lap_end)
        ].copy()

        s = s[
            (s["lap_number"] > 1)
            &
            (s["lap_duration"] > 0)
        ].copy()

        if "is_pit_out_lap" in s.columns:
            s = s[s["is_pit_out_lap"] != True].copy()

        # Remove pit-in lap for every stint except the final stint.
        if stint_idx != n_stints - 1:
            s = s[
                s["lap_number"] != lap_end
            ].copy()

        if len(s) < 2:
            continue

        s["TyreAge"] = (
            tyre_age_start
            + (s["lap_number"] - lap_start)
        )

        median_laptime = s["lap_duration"].median()

        mad = np.median(
            np.abs(
                s["lap_duration"] - median_laptime
            )
        )

        robust_sigma = 1.4826 * mad
        threshold = max(3.5 * robust_sigma, 2.5)

        clean = s[
            np.abs(
                s["lap_duration"] - median_laptime
            )
            <= threshold
        ].copy()

        if len(clean) < 2:
            continue

        average_pace = clean["lap_duration"].mean()
        median_pace = clean["lap_duration"].median()
        best_lap = clean["lap_duration"].min()

        clean["DeltaToBest"] = (
            clean["lap_duration"] - best_lap
        )

        deg_slope = np.nan

        if (
            len(clean) >= 4
            and clean["TyreAge"].nunique() >= 4
        ):
            slope, _ = np.polyfit(
                clean["TyreAge"],
                clean["lap_duration"],
                1
            )
            deg_slope = float(slope)

        clean["Driver"] = driver
        clean["Position"] = finish_position
        clean["Stint"] = stint_number
        clean["Compound"] = compound
        clean["DegSlope"] = deg_slope

        clean_frames.append(clean)

        summary_rows.append({
            "Position": finish_position,
            "Driver": driver,
            "DriverNumber": driver_num,
            "Stint": stint_number,
            "Compound": compound,
            "LapStart": lap_start,
            "LapEnd": lap_end,
            "TyreAgeStart": tyre_age_start,
            "ValidLaps": len(clean),
            "AveragePace": average_pace,
            "MedianPace": median_pace,
            "BestLap": best_lap,
            "DegSlope": deg_slope
        })

if not clean_frames:
    raise RuntimeError("Tidak ada valid clean stint data.")

clean_laps = pd.concat(clean_frames, ignore_index=True)

summary = (
    pd.DataFrame(summary_rows)
    .sort_values(["Position", "Stint"])
    .reset_index(drop=True)
)

display_summary = summary.copy()

display_summary["Average Pace"] = display_summary["AveragePace"].apply(
    format_seconds
)
display_summary["Median Pace"] = display_summary["MedianPace"].apply(
    format_seconds
)
display_summary["Best Lap"] = display_summary["BestLap"].apply(
    format_seconds
)
display_summary["Deg / Lap"] = display_summary["DegSlope"].apply(
    lambda x: f"{x:+.3f} s/lap" if pd.notna(x) else "-"
)

print("\n" + "=" * 100)
print("TOP 10 — TYRE DEGRADATION & AVERAGE STINT PACE")
print("=" * 100)

display(
    display_summary[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "ValidLaps",
            "Average Pace",
            "Median Pace",
            "Best Lap",
            "Deg / Lap"
        ]
    ]
)

# ------------------------------------------------
# Degradation plots
# ------------------------------------------------

fig, axes = plt.subplots(
    5,
    2,
    figsize=(17, 24)
)

axes = axes.flatten()

for plot_index, (_, result_row) in enumerate(top10.iterrows()):
    ax = axes[plot_index]

    driver = result_row["Driver"]
    position = int(result_row["position"])

    driver_data = clean_laps[
        clean_laps["Driver"].eq(driver)
    ]

    driver_summary = summary[
        summary["Driver"].eq(driver)
    ]

    if driver_data.empty:
        ax.set_title(f"P{position} — {driver}\nNo data")
        ax.axis("off")
        continue

    for _, sr in driver_summary.iterrows():
        stint_num = int(sr["Stint"])
        compound = sr["Compound"]

        color = compound_colors.get(compound, "black")
        style = line_styles[(stint_num - 1) % len(line_styles)]

        s = driver_data[
            driver_data["Stint"].eq(stint_num)
        ].sort_values("TyreAge")

        ax.scatter(
            s["TyreAge"],
            s["DeltaToBest"],
            color=color,
            s=32,
            alpha=0.75
        )

        if (
            pd.notna(sr["DegSlope"])
            and len(s) >= 4
        ):
            x_fit = np.linspace(
                s["TyreAge"].min(),
                s["TyreAge"].max(),
                50
            )

            slope, intercept = np.polyfit(
                s["TyreAge"],
                s["DeltaToBest"],
                1
            )

            y_fit = slope * x_fit + intercept

            ax.plot(
                x_fit,
                y_fit,
                color=color,
                linestyle=style,
                linewidth=2,
                label=(
                    f"S{stint_num} {compound} "
                    f"{sr['DegSlope']:+.3f}s/lap"
                )
            )
        else:
            ax.plot(
                s["TyreAge"],
                s["DeltaToBest"],
                color=color,
                linestyle=style,
                linewidth=1.5,
                label=f"S{stint_num} {compound}"
            )

    ax.axhline(0, linewidth=0.8, alpha=0.4)

    ax.set_title(
        f"P{position} — {driver}",
        fontsize=13,
        fontweight="bold"
    )
    ax.set_xlabel("Tyre Age (laps)")
    ax.set_ylabel("Delta to Stint Best (s)")
    ax.grid(alpha=0.2, linestyle="--")
    ax.legend(fontsize=8)

fig.suptitle(
    "MADRID GP 2026 — TOP 10 OBSERVED TYRE DEGRADATION\n"
    "Positive slope = lap time tends to increase as tyre ages",
    fontsize=18,
    fontweight="bold",
    y=1.005
)

plt.tight_layout()
plt.show()

# ------------------------------------------------
# Average pace per stint
# ------------------------------------------------

plot_summary = summary.copy()

plot_summary["Label"] = (
    "P"
    + plot_summary["Position"].astype(int).astype(str)
    + " "
    + plot_summary["Driver"]
    + " | S"
    + plot_summary["Stint"].astype(int).astype(str)
    + " "
    + plot_summary["Compound"]
)

plot_summary = plot_summary.iloc[::-1]

bar_colors = [
    compound_colors.get(c, "black")
    for c in plot_summary["Compound"]
]

fig, ax = plt.subplots(figsize=(15, 12))

bars = ax.barh(
    plot_summary["Label"],
    plot_summary["AveragePace"],
    color=bar_colors,
    alpha=0.85
)

min_pace = plot_summary["AveragePace"].min()
max_pace = plot_summary["AveragePace"].max()

ax.set_xlim(
    min_pace - 1.0,
    max_pace + 2.2
)

for bar, (_, row) in zip(bars, plot_summary.iterrows()):
    deg_text = (
        f"{row['DegSlope']:+.3f}s/lap"
        if pd.notna(row["DegSlope"])
        else "-"
    )

    ax.text(
        row["AveragePace"] + 0.05,
        bar.get_y() + bar.get_height() / 2,
        f"{format_seconds(row['AveragePace'])} | deg {deg_text}",
        va="center",
        fontsize=8,
        fontweight="bold"
    )

ax.set_title(
    "MADRID GP 2026 — AVERAGE PACE PER STINT\n"
    "Lower = Faster",
    fontsize=16,
    fontweight="bold",
    pad=16
)
ax.set_xlabel("Average Clean Lap Time (seconds)")
ax.set_ylabel("Driver / Stint / Compound")
ax.grid(axis="x", linestyle="--", alpha=0.25)

plt.tight_layout()
plt.show()

# ------------------------------------------------
# Ranking
# ------------------------------------------------

deg_ranking = summary[
    summary["DegSlope"].notna()
].sort_values("DegSlope").copy()

deg_table = deg_ranking[
    [
        "Position",
        "Driver",
        "Stint",
        "Compound",
        "LapStart",
        "LapEnd",
        "ValidLaps",
        "AveragePace",
        "DegSlope"
    ]
].copy()

deg_table["Average Pace"] = deg_table["AveragePace"].apply(
    format_seconds
)
deg_table["Deg / Lap"] = deg_table["DegSlope"].map(
    lambda x: f"{x:+.3f} s/lap"
)

print("\n" + "=" * 100)
print("TYRE DEGRADATION RANKING — LOWEST TO HIGHEST")
print("=" * 100)

display(
    deg_table[
        [
            "Position",
            "Driver",
            "Stint",
            "Compound",
            "LapStart",
            "LapEnd",
            "ValidLaps",
            "Average Pace",
            "Deg / Lap"
        ]
    ]
)

print(
    "\nNOTE: slope ini adalah observed degradation proxy, "
    "bukan tyre degradation murni; fuel burn, traffic dan track evolution "
    "masih dapat memengaruhi hasil."
)
