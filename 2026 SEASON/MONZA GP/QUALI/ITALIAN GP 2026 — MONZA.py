# ================================================================
# ITALIAN GP 2026 — MONZA
# Q3 TOP 10 TABLE
# P10 -> P1 | Q3 TIME | GAP TO POLE
# OPENF1 — ONE CELL
# ================================================================

!pip install -q requests pandas numpy matplotlib

import time, random, requests
import pandas as pd
import numpy as np

YEAR = 2026
BASE = "https://api.openf1.org/v1"
LAST_REQUEST = 0
MIN_INTERVAL = 1.15

http = requests.Session()
http.headers.update({"Accept":"application/json","User-Agent":"Mozilla/5.0"})

def api_get(endpoint, params=None, allow_empty=False, retries=10):
    global LAST_REQUEST
    for attempt in range(retries):
        wait = MIN_INTERVAL - (time.time() - LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        r = http.get(f"{BASE}/{endpoint}", params=params, timeout=90)
        LAST_REQUEST = time.time()

        if r.status_code == 429:
            w = min(4 + attempt*4, 35) + random.uniform(.2,.8)
            print(f"429 {endpoint} → retry {attempt+1}/{retries} in {w:.1f}s")
            time.sleep(w)
            continue

        if r.status_code != 200:
            raise RuntimeError(f"{endpoint}: HTTP {r.status_code}\n{r.text[:500]}")

        data = r.json()
        if not data and not allow_empty:
            raise RuntimeError(f"No data from {endpoint}")
        return data

    raise RuntimeError(f"{endpoint} gagal setelah {retries} retry")

def parse_dt(x):
    return pd.to_datetime(x, format="mixed", utc=True, errors="coerce")

def find_monza_session(name):
    sessions = pd.DataFrame(api_get("sessions", {"year": YEAR}))

    loc = sessions.get("location", pd.Series("", index=sessions.index)).astype(str)
    circ = sessions.get("circuit_short_name", pd.Series("", index=sessions.index)).astype(str)
    meet = sessions.get("meeting_name", pd.Series("", index=sessions.index)).astype(str)

    mask = (
        loc.str.contains("Monza", case=False, na=False)
        | circ.str.contains("Monza", case=False, na=False)
        | meet.str.contains("Italian", case=False, na=False)
    )

    x = sessions[
        mask &
        sessions["session_name"].astype(str).str.lower().eq(name.lower())
    ].copy()

    if x.empty:
        raise RuntimeError(f"Monza {name} 2026 tidak ditemukan")

    x["_date"] = parse_dt(x["date_start"])
    return x.sort_values("_date").iloc[-1]

def q3_value(v):
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        try:
            return float(v[2]) if v[2] is not None else np.nan
        except:
            return np.nan
    return np.nan

def fmt(sec):
    if pd.isna(sec):
        return "-"
    return f"{int(sec//60)}:{sec%60:06.3f}"

session = find_monza_session("Qualifying")
SESSION_KEY = int(session["session_key"])

print("MONZA QUALIFYING")
print("Session key:", SESSION_KEY)

drivers = pd.DataFrame(api_get("drivers", {"session_key": SESSION_KEY}))
drivers["driver_number"] = pd.to_numeric(drivers["driver_number"], errors="coerce")
drivers = drivers.dropna(subset=["driver_number"]).drop_duplicates("driver_number")
drivers["driver_number"] = drivers["driver_number"].astype(int)

driver_map = drivers.set_index("driver_number")["name_acronym"].to_dict()
name_map = drivers.set_index("driver_number")["full_name"].to_dict()
team_map = drivers.set_index("driver_number")["team_name"].to_dict()

results = pd.DataFrame(api_get("session_result", {"session_key": SESSION_KEY}))
results["position"] = pd.to_numeric(results["position"], errors="coerce")
results["driver_number"] = pd.to_numeric(results["driver_number"], errors="coerce")

results["Q3_seconds"] = results["duration"].apply(q3_value)

q3 = results[results["Q3_seconds"].notna()].copy()
q3 = q3.sort_values("position")

if q3.empty:
    raise RuntimeError("Tidak ada Q3 data")

pole = q3["Q3_seconds"].min()

q3["Driver"] = q3["driver_number"].astype(int).map(driver_map)
q3["Name"] = q3["driver_number"].astype(int).map(name_map)
q3["Team"] = q3["driver_number"].astype(int).map(team_map)
q3["Q3 Time"] = q3["Q3_seconds"].apply(fmt)
q3["Gap"] = q3["Q3_seconds"] - pole
q3["Gap to Pole"] = q3["Gap"].map(lambda x: "POLE" if abs(x) < 1e-9 else f"+{x:.3f}s")

table = q3[
    ["position","Driver","Name","Team","Q3 Time","Gap to Pole"]
].copy()

table["position"] = table["position"].astype(int)
table = table.rename(columns={"position":"Pos"}).sort_values("Pos", ascending=False)

print("\n" + "="*100)
print("MONZA 2026 — Q3 RESULT P10 -> P1")
print("="*100)

display(table.reset_index(drop=True))
