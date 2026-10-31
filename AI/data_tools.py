# Tools the chatbot uses for live numbers. The values come from the database
# and the ML models, the language model only explains them.
import json
import sys
from pathlib import Path

from langchain_core.tools import tool

sys.path.append(str(Path(__file__).resolve().parent.parent / "Backend"))
import services
from alert_rules import evaluate


@tool
def Get_current_status(department: str = ""):
    """Latest numbers from the hospital database: beds occupied, occupancy, ED arrivals,
    ED waiting time, nurses present, staff availability and alert colour.
    Use it for questions like "how many ICU beds are occupied" or "which departments are Red".
    department is optional, for example "ICU" or "Emergency". Leave it empty for all departments."""
    rows = services.latest_rows()
    if department.strip():
        rows = [r for r in rows if department.lower().strip() in r["department"].lower()]
        if not rows:
            return "No department found with that name."
    result = {"data_as_of": str(rows[0]["timestamp"]), "departments": []}
    for r in rows:
        result["departments"].append({
            "department": r["department"],
            "occupied_beds": r["occupied_beds"], "total_beds": r["total_beds"],
            "occupancy_pct": round(float(r["occupancy_rate"]) * 100, 1),
            "arrivals_this_hour": r["arrivals"], "avg_wait_min": float(r["avg_wait_min"]),
            "nurses_present": r["nurses_present"], "nurses_scheduled": r["nurses_scheduled"],
            "staff_availability_pct": float(r["staff_availability_pct"]),
            "alert_level": r["alert_level"]})
    if not department.strip():
        k = services.kpis(rows)
        result["hospital_totals"] = {"occupancy_pct": k["occupancy"]["value"],
                                     "staff_availability_pct": k["staff"]["value"]}
    return json.dumps(result)


@tool
def Get_capacity_status():
    """Current hospital capacity level (0 is normal, then 1, 2, 3) from the overcrowding plan,
    the reasons for it, the recommended actions and the departments above Green.
    Use it for "what is the capacity level" or "what actions should we take now"."""
    rows = services.latest_rows()
    ev = evaluate(rows)
    not_green = [{"department": d["department"], "level": d["level"], "reason": d["reasons"]}
                 for d in ev["departments"] if d["level"] != "Green"]
    return json.dumps({"data_as_of": str(rows[0]["timestamp"]),
                       "capacity_level": ev["capacity_level"], "triggered_by": ev["reasons"],
                       "recommended_actions": ev["actions"], "departments_not_green": not_green})


@tool
def Get_forecast(metric: str = "arrivals"):
    """ML forecast for the next 6 hours.
    metric can be "arrivals" (ED patients per hour), "occupancy" (hospital beds in %)
    or "wait" (ED waiting time in minutes). Use it for questions about the future."""
    if metric not in ("arrivals", "occupancy", "wait"):
        return "metric must be arrivals, occupancy or wait."
    f = services.forecast(metric, 6)
    return json.dumps({"metric": metric, "source": "ML forecast model",
                       "forecast": [{"hour": str(x["hour"]), "value": x["value"]} for x in f]})


@tool
def Get_spike_status():
    """Checks if the newest ED arrivals are unusually high for that hour and weekday.
    Use it for "is there a surge in the ED" or "are arrivals unusual"."""
    r = services.spike_status()
    return json.dumps({"data_as_of": str(r["timestamp"]), "arrivals": r["arrivals"],
                       "usual_arrivals": r["usual_arrivals"], "z_score": r["z_score"],
                       "is_anomaly": r["is_anomaly"]})
