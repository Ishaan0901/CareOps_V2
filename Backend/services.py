"""Shared data logic for CareOps AI (used by the FastAPI app AND the AI agent tools).
Reads PostgreSQL, runs alert rules, ML forecast and spike detection.
'Current' = latest timestamp in the database (the dataset is synthetic)."""
import os, sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT / "ML"))
sys.path.append(str(Path(__file__).resolve().parent))
import ml_tools  # noqa  (ML/ml_tools.py: forecast model + anomaly rule)
from alert_rules import evaluate, up, staff_level, arrivals_level, NAMES

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

# Latest hour of data for every department
LATEST = """
    SELECT d.department, d.target_patients_per_nurse, h.* FROM hourly_metrics h
    JOIN departments d ON d.department_id = h.department_id
    WHERE h.timestamp = (SELECT MAX(timestamp) FROM hourly_metrics)
    ORDER BY h.department_id
"""

def hour_label(ts):
    h = pd.Timestamp(ts).hour
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"

def latest_rows():
    with engine.connect() as c:
        return [dict(r) for r in c.execute(text(LATEST)).mappings().all()]

# ---------- ML ----------
def ed_history(limit=168):
    """Last 168 hours of ED data, oldest first (the forecast model needs this)."""
    q = text("""SELECT timestamp, hour, day_of_week, arrivals, occupancy_rate,
                avg_wait_min, staff_availability_pct FROM hourly_metrics
                WHERE department_id = 1 ORDER BY timestamp DESC LIMIT :l""")
    with engine.connect() as c:
        df = pd.DataFrame(c.execute(q, {"l": limit}).mappings().all())
    df = df.sort_values("timestamp").reset_index(drop=True)
    for col in ["arrivals", "occupancy_rate", "avg_wait_min", "staff_availability_pct"]:
        df[col] = df[col].astype(float)   # DB gives Decimal, model needs float
    return df

def forecast_arrivals(steps=6):
    """Forecast ED arrivals for the next `steps` hours (each step feeds the next)."""
    h = ed_history()
    out = []
    for _ in range(steps):
        ts = h["timestamp"].iloc[-1] + pd.Timedelta(hours=1)
        p = float(ml_tools.predict_arrivals(h, ts))
        out.append({"hour": ts, "arrivals": round(p, 1)})
        row = h.iloc[-1].to_dict()
        row.update(timestamp=ts, hour=ts.hour, day_of_week=ts.dayofweek, arrivals=p)
        h = pd.concat([h, pd.DataFrame([row])], ignore_index=True).tail(168)
    return out

def spike_status():
    """Is the latest ED hour an unusual arrivals spike?"""
    last = ed_history(2).iloc[-1]
    r = ml_tools.detect_anomaly(int(last["hour"]), int(last["day_of_week"]), int(last["arrivals"]))
    return {"timestamp": last["timestamp"], "arrivals": int(last["arrivals"]), **r}

# ---------- Dashboard ----------
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
    ev = {d["department_id"]: d for d in evaluate(rows)["departments"]}
    cards = [{"n": r["department"], "used": r["occupied_beds"], "total": r["total_beds"],
              "st": ev[r["department_id"]]["level"].lower(),
              "tag": f"{ev[r['department_id']]['level']} · Nurses 1:{r['target_patients_per_nurse']}"}
             for r in rows]
    return {"departments": cards,
            "staff": {"present": sum(r["nurses_present"] for r in rows),
                      "required": sum(r["nurses_scheduled"] for r in rows)}}

def alerts(rows):
    ev, sp = evaluate(rows), spike_status()
    order = {n: i for i, n in enumerate(NAMES)}
    items = [{"t": f"{d['department']}: {', '.join(d['reasons'])}", "c": d["level"].lower(), "src": "Rule"}
             for d in sorted(ev["departments"], key=lambda d: -order[d["level"]]) if d["level"] != "Green"]
    if not items:
        items.append({"t": "All departments normal", "c": "green", "src": "Rule"})
    if sp["is_anomaly"]:
        items.append({"t": f"ED arrivals spike, z-score {sp['z_score']}", "c": "red", "label": "Anomaly", "src": "ML"})
    else:
        items.append({"t": f"ED arrivals normal, z-score {sp['z_score']}", "c": "green", "src": "ML"})
    store_alerts(rows, ev, sp)
    return {"capacity": {"level": ev["capacity_level"], "reasons": ev["reasons"], "actions": ev["actions"]},
            "alerts": items}

def store_alerts(rows, ev, sp):
    """Save alerts to the alerts table once per data timestamp."""
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
    with engine.connect() as c:
        return [dict(r) for r in c.execute(text(
            "SELECT id, created_at, data_time, department_id, level, capacity_level, message, source "
            "FROM alerts ORDER BY id DESC LIMIT :l"), {"l": limit}).mappings().all()]

def trend(metric, hours=48):
    """Past values (+ ML forecast and anomalies for ED arrivals) for the trend chart."""
    if metric == "occupancy":
        q = "SELECT timestamp, SUM(occupied_beds)*100.0/SUM(total_beds) AS v FROM hourly_metrics GROUP BY timestamp ORDER BY timestamp DESC LIMIT :h"
        title, suf = "Hospital occupancy (%): past values", "%"
    elif metric == "wait":
        q = "SELECT timestamp, avg_wait_min AS v FROM hourly_metrics WHERE department_id=1 ORDER BY timestamp DESC LIMIT :h"
        title, suf = "ED waiting time (min): past values", " min"
    else:
        metric = "arrivals"
        q = "SELECT timestamp, arrivals AS v FROM hourly_metrics WHERE department_id=1 ORDER BY timestamp DESC LIMIT :h"
        title, suf = "ED arrivals: past and forecast", ""
    with engine.connect() as c:
        rows = list(reversed(c.execute(text(q), {"h": hours}).mappings().all()))
    past = [round(float(r["v"]), 1) for r in rows]
    fc, an, peak = [], [], "-"
    if metric == "arrivals":
        for i, r in enumerate(rows):    # ML anomaly check for each past hour
            ts = pd.Timestamp(r["timestamp"])
            if ml_tools.detect_anomaly(ts.hour, ts.dayofweek, int(r["v"]))["is_anomaly"]:
                an.append(i)
        f = forecast_arrivals(6)
        fc = [x["arrivals"] for x in f]
        peak = hour_label(max(f, key=lambda x: x["arrivals"])["hour"])
    return {"title": title, "suf": suf, "past": past, "fc": fc, "an": an, "peak": peak}

# ---------- Knowledge base ----------
def documents():
    """List of [title, file name] for the PDFs in data/RAG_Pdfs."""
    out = []
    for f in sorted((ROOT / "data" / "RAG_Pdfs").glob("*.pdf")):
        title = f.stem.split("_", 1)[1].replace("_", " ") if f.stem[:2].isdigit() else f.stem
        out.append([title, f.name])
    return out
