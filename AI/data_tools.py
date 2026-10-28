"""AI agent tools for LIVE DATA (database, alert rules, ML models).
No LLM guessing: every number comes from PostgreSQL or the ML models in services.py."""
import json, sys
from pathlib import Path
from langchain_core.tools import tool

sys.path.append(str(Path(__file__).resolve().parent.parent / "Backend"))
import services as s
from alert_rules import evaluate


@tool
def Get_current_status(department: str = ""):
    '''
    Get the LATEST live numbers from the hospital database: bed occupancy, ED arrivals, ED waiting time, nurses present, staff availability and alert colour (Green/Yellow/Orange/Red).

    Use this for questions about current or latest numbers, for example "How many ICU beds are occupied?", "What is the ED waiting time now?" or "Which departments are at Red?".
    Input: department (optional) - part of a department name, such as "ICU" or "Emergency". Leave empty for hospital totals and all departments.
    '''
    rows = s.latest_rows()
    if department.strip():
        rows = [r for r in rows if department.lower().strip() in r["department"].lower()]
        if not rows:
            return "No department found with that name."
    out = {"data_as_of": str(rows[0]["timestamp"]), "departments": [
        {"department": r["department"], "occupied_beds": r["occupied_beds"], "total_beds": r["total_beds"],
         "occupancy_pct": round(float(r["occupancy_rate"]) * 100, 1), "arrivals_this_hour": r["arrivals"],
         "avg_wait_min": float(r["avg_wait_min"]), "nurses_present": r["nurses_present"],
         "nurses_scheduled": r["nurses_scheduled"], "staff_availability_pct": float(r["staff_availability_pct"]),
         "alert_level": r["alert_level"]} for r in rows]}
    if not department.strip():
        k = s.kpis(rows)
        out["hospital_totals"] = {"occupancy_pct": k["occupancy"]["value"], "staff_availability_pct": k["staff"]["value"]}
    return json.dumps(out)


@tool
def Get_capacity_status():
    '''
    Get the CURRENT hospital capacity level (0 = normal, 1, 2 or 3) from the overcrowding plan rules, why it was triggered, the recommended actions, and which departments are above Green.

    Use this for questions like "What is the current capacity level?", "Are we in surge?" or "What actions should we take now?".
    '''
    rows = s.latest_rows()
    ev = evaluate(rows)
    return json.dumps({"data_as_of": str(rows[0]["timestamp"]), "capacity_level": ev["capacity_level"],
                       "triggered_by": ev["reasons"], "recommended_actions": ev["actions"],
                       "departments_not_green": [{"department": d["department"], "level": d["level"], "reason": d["reasons"]}
                                                 for d in ev["departments"] if d["level"] != "Green"]})


@tool
def Get_arrival_forecast():
    '''
    Get the ML forecast of ED (Emergency Department) patient arrivals for the NEXT 6 hours.

    Use this for questions about the future, such as "How many patients will arrive in the next hours?" or "When is the next peak?". It only forecasts ED arrivals, not occupancy or waiting time.
    '''
    f = s.forecast_arrivals(6)
    return json.dumps({"model": "ML forecast (XGBoost), ED arrivals per hour",
                       "forecast": [{"hour": str(x["hour"]), "predicted_arrivals": x["arrivals"]} for x in f]})


@tool
def Get_spike_status():
    '''
    Check whether the latest ED arrivals are an unusual spike (anomaly) compared with the usual pattern for that hour and weekday.

    Use this for questions like "Is there a surge in the ED?" or "Are arrivals unusual right now?".
    '''
    r = s.spike_status()
    return json.dumps({"data_as_of": str(r["timestamp"]), "arrivals": r["arrivals"],
                       "usual_arrivals": r["usual_arrivals"], "z_score": r["z_score"], "is_anomaly": r["is_anomaly"]})
