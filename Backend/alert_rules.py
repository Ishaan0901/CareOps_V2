# Alert rules from CGH-OPS-002 (colours) and CGH-OPS-004 (capacity levels)
NAMES = ["Green", "Yellow", "Orange", "Red"]

def up(v, y, o, r):      # higher value = worse
    return 3 if v >= r else 2 if v >= o else 1 if v >= y else 0

def staff_level(p):      # lower value = worse
    return 3 if p < 70 else 2 if p < 85 else 1 if p < 95 else 0

def arrivals_level(a):   # ED arrivals per hour
    return 3 if a > 100 else 2 if a > 60 else 1 if a > 40 else 0

def dept_alert(r):
    occ = float(r["occupancy_rate"]) * 100
    wait = float(r["avg_wait_min"])
    reasons = []
    # Occupancy: ED (id 1), ICU (id 2), others use hospital-wide cuts
    cuts = {1: (70, 80, 90), 2: (80, 85, 95)}.get(r["department_id"], (75, 85, 90))
    reasons.append((up(occ, *cuts), f"Occupancy {occ:.1f}%"))
    s = float(r["staff_availability_pct"])
    reasons.append((staff_level(s), f"Staff availability {s}%"))
    if r["department_id"] == 1:  # ED-only indicators
        reasons.append((up(wait, 30, 45, 60), f"ED wait {wait} min"))
        reasons.append((arrivals_level(r["arrivals"]), f"ED arrivals {r['arrivals']}/hr"))
    top = max(x[0] for x in reasons)  # highest colour applies
    why = [t for lv, t in reasons if lv == top and top > 0]
    return {"department_id": r["department_id"], "department": r["department"], "level": NAMES[top], "reasons": why}

ACTIONS = {
    1: ["List today's discharges, inform Bed Manager", "Prioritise cleaning of vacated beds (within 30 min)",
        "Open ED fast track", "Extra bed huddle", "Lab and radiology prioritise ED"],
    2: ["Duty Manager takes charge, informs Medical Superintendent", "Open discharge lounge",
        "Move boarded patients to wards", "Call in float pool nurses", "Review elective admissions",
        "Up to 20 surge beds with Duty Manager approval"],
    3: ["Medical Superintendent declares Level 3 and informs Hospital Administrator",
        "Postpone non-urgent surgeries and admissions", "Up to 40 surge beds",
        "Command meeting every 2 hours", "Request mutual aid"],
}

def capacity_level(rows):
    hosp = sum(r["occupied_beds"] for r in rows) / sum(r["total_beds"] for r in rows) * 100
    ed = next(r for r in rows if r["department_id"] == 1)
    ed_occ = float(ed["occupancy_rate"]) * 100
    wait = float(ed["avg_wait_min"])
    staff = sum(r["nurses_present"] for r in rows) / sum(r["nurses_scheduled"] for r in rows) * 100
    checks = [  # (level, condition, reason)
        (3, hosp >= 95, f"Hospital occupancy {hosp:.1f}%"), (3, ed_occ >= 95, f"ED occupancy {ed_occ:.1f}%"),
        (3, wait >= 60, f"ED wait {wait} min"), (3, staff < 70, f"Staff availability {staff:.1f}%"),
        (2, 90 <= hosp < 95, f"Hospital occupancy {hosp:.1f}%"), (2, 90 <= ed_occ < 95, f"ED occupancy {ed_occ:.1f}%"),
        (2, 45 <= wait < 60, f"ED wait {wait} min"), (2, 70 <= staff < 85, f"Staff availability {staff:.1f}%"),
        (1, 85 <= hosp < 90, f"Hospital occupancy {hosp:.1f}%"), (1, 80 <= ed_occ < 90, f"ED occupancy {ed_occ:.1f}%"),
        (1, 30 <= wait < 45, f"ED wait {wait} min"),
    ]
    lvl = max([l for l, ok, _ in checks if ok], default=0)
    why = [t for l, ok, t in checks if ok and l == lvl]
    acts = [a for k in range(1, lvl + 1) for a in ACTIONS[k]]
    return {"capacity_level": lvl, "reasons": why, "actions": acts}

def evaluate(rows):
    return {**capacity_level(rows), "departments": [dept_alert(r) for r in rows]}
