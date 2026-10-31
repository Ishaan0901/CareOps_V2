# Functions used by both the API (main.py) and the chatbot tools.
# They read the database, apply the alert rules and call the ML models.
# "Current" means the newest hour in the database (the data is synthetic).
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT / "ML"))
sys.path.append(str(Path(__file__).resolve().parent))
import ml_tools
from alert_rules import evaluate, up, staff_level, arrivals_level, NAMES

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

# newest hour, one row per department
LATEST = """
    SELECT d.department, d.target_patients_per_nurse, h.*
    FROM hourly_metrics h
    JOIN departments d ON d.department_id = h.department_id
    WHERE h.timestamp = (SELECT MAX(timestamp) FROM hourly_metrics)
    ORDER BY h.department_id
"""

# one value per hour for each metric (hospital level for occupancy, ED for the others)
SERIES_SQL = {
    "arrivals": "SELECT timestamp, arrivals AS v FROM hourly_metrics WHERE department_id = 1",
    "wait": "SELECT timestamp, avg_wait_min AS v FROM hourly_metrics WHERE department_id = 1",
    "occupancy": """SELECT timestamp, SUM(occupied_beds) * 100.0 / SUM(total_beds) AS v
                    FROM hourly_metrics GROUP BY timestamp""",
}


def hour_label(ts):
    h = pd.Timestamp(ts).hour
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"


def latest_rows():
    with engine.connect() as c:
        return [dict(r) for r in c.execute(text(LATEST)).mappings().all()]


def series(metric, hours):
    """Last `hours` values of a metric as a DataFrame (timestamp, v), oldest first."""
    q = text(f"SELECT * FROM ({SERIES_SQL[metric]}) s ORDER BY timestamp DESC LIMIT :h")
    with engine.connect() as c:
        rows = c.execute(q, {"h": hours}).mappings().all()
    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    df["v"] = df["v"].astype(float)
    return df


def forecast(metric="arrivals", steps=6):
    s = series(metric, 168)
    return ml_tools.forecast(metric, s["v"].values, s["timestamp"].iloc[-1], steps)


def spike_status():
    """Is the newest ED hour unusually busy compared with the same hour and weekday?"""
    s = series("arrivals", 1).iloc[-1]
    ts = pd.Timestamp(s["timestamp"])
    r = ml_tools.detect_anomaly(ts.hour, ts.dayofweek, int(s["v"]))
    return {"timestamp": ts, "arrivals": int(s["v"]), **r}


def kpis(rows):
    occ = sum(r["occupied_beds"] for r in rows) / sum(r["total_beds"] for r in rows) * 100
    ed = next(r for r in rows if r["department_id"] == 1)
    staff = sum(r["nurses_present"] for r in rows) / sum(r["nurses_scheduled"] for r in rows) * 100
    wait, arr = float(ed["avg_wait_min"]), int(ed["arrivals"])
    return {
        "as_of": str(ed["timestamp"]),
        "occupancy": {"value": round(occ), "level": NAMES[up(occ, 75, 85, 90)].lower()},
        "wait": {"value": round(wait), "level": NAMES[up(wait, 30, 45, 60)].lower()},
        "arrivals": {"value": arr, "level": NAMES[arrivals_level(arr)].lower()},
        "staff": {"value": round(staff), "level": NAMES[staff_level(staff)].lower()},
    }


def departments(rows):
    levels = {d["department_id"]: d["level"] for d in evaluate(rows)["departments"]}
    cards = []
    for r in rows:
        level = levels[r["department_id"]]
        cards.append({"n": r["department"], "used": r["occupied_beds"], "total": r["total_beds"],
                      "st": level.lower(),
                      "tag": f"{level} · Nurses 1:{r['target_patients_per_nurse']}"})
    staff = {"present": sum(r["nurses_present"] for r in rows),
             "required": sum(r["nurses_scheduled"] for r in rows)}
    return {"departments": cards, "staff": staff}


def alerts(rows):
    ev = evaluate(rows)
    sp = spike_status()
    rank = {n: i for i, n in enumerate(NAMES)}
    items = []
    for d in sorted(ev["departments"], key=lambda d: -rank[d["level"]]):
        if d["level"] != "Green":
            items.append({"t": f"{d['department']}: {', '.join(d['reasons'])}",
                          "c": d["level"].lower(), "src": "Rule"})
    if not items:
        items.append({"t": "All departments normal", "c": "green", "src": "Rule"})
    if sp["is_anomaly"]:
        items.append({"t": f"ED arrivals spike, z-score {sp['z_score']}",
                      "c": "red", "label": "Anomaly", "src": "ML"})
    else:
        items.append({"t": f"ED arrivals normal, z-score {sp['z_score']}", "c": "green", "src": "ML"})
    save_alerts(rows, ev, sp)
    return {"capacity": {"level": ev["capacity_level"], "reasons": ev["reasons"],
                         "actions": ev["actions"]}, "alerts": items}


def save_alerts(rows, ev, sp):
    """Store the alerts in the alerts table (only once for each hour of data)."""
    ts = rows[0]["timestamp"]
    with engine.begin() as c:
        c.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS data_time TIMESTAMP"))
        if c.execute(text("SELECT 1 FROM alerts WHERE data_time = :t LIMIT 1"), {"t": ts}).first():
            return
        ins = text("""INSERT INTO alerts (department_id, level, capacity_level, message, source, data_time)
                      VALUES (:d, :l, :c, :m, :s, :t)""")
        for d in ev["departments"]:
            if d["level"] != "Green":
                c.execute(ins, {"d": d["department_id"], "l": d["level"], "c": ev["capacity_level"],
                                "m": ", ".join(d["reasons"]), "s": "policy", "t": ts})
        if sp["is_anomaly"]:
            c.execute(ins, {"d": 1, "l": "Red", "c": ev["capacity_level"],
                            "m": f"ED arrivals spike, z-score {sp['z_score']}", "s": "ml", "t": ts})


def alert_history(limit=50):
    q = text("""SELECT id, created_at, data_time, department_id, level, capacity_level, message, source
                FROM alerts ORDER BY id DESC LIMIT :l""")
    with engine.connect() as c:
        return [dict(r) for r in c.execute(q, {"l": limit}).mappings().all()]


def trend(metric, hours=48):
    """Data for the trend graph: past values, 6 hour forecast and anomaly points."""
    titles = {"arrivals": ("ED arrivals: past and forecast", ""),
              "occupancy": ("Hospital occupancy (%): past and forecast", "%"),
              "wait": ("ED waiting time (min): past and forecast", " min")}
    if metric not in titles:
        metric = "arrivals"
    past = series(metric, hours)
    fc = forecast(metric, 6)
    anomalies = []
    if metric == "arrivals":   # the anomaly rule only exists for ED arrivals
        for i, row in past.iterrows():
            ts = pd.Timestamp(row["timestamp"])
            if ml_tools.detect_anomaly(ts.hour, ts.dayofweek, int(row["v"]))["is_anomaly"]:
                anomalies.append(i)
    peak = max(fc, key=lambda x: x["value"])
    return {"title": titles[metric][0], "suf": titles[metric][1],
            "past": [round(v, 1) for v in past["v"]], "fc": [x["value"] for x in fc],
            "an": anomalies, "peak": hour_label(peak["hour"])}


def documents():
    """[title, file name] for every PDF in data/RAG_Pdfs."""
    out = []
    for f in sorted((ROOT / "data" / "RAG_Pdfs").glob("*.pdf")):
        name = f.stem.split("_", 1)[1] if f.stem[:2].isdigit() else f.stem
        out.append([name.replace("_", " "), f.name])
    return out
