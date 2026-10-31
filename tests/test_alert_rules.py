# Tests for the alert rules. Run from the project folder:  pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "Backend"))
from alert_rules import dept_alert, capacity_level, staff_level, arrivals_level


def row(dept_id=1, occupancy=0.5, wait=20, arrivals=25, staff=100, occupied=50, total=100,
        present=10, scheduled=10):
    return {"department_id": dept_id, "department": "Test", "occupancy_rate": occupancy,
            "avg_wait_min": wait, "arrivals": arrivals, "staff_availability_pct": staff,
            "occupied_beds": occupied, "total_beds": total,
            "nurses_present": present, "nurses_scheduled": scheduled}


def test_normal_department_is_green():
    assert dept_alert(row(dept_id=3))["level"] == "Green"


def test_icu_occupancy_levels():
    assert dept_alert(row(dept_id=2, occupancy=0.82))["level"] == "Yellow"
    assert dept_alert(row(dept_id=2, occupancy=0.90))["level"] == "Orange"
    assert dept_alert(row(dept_id=2, occupancy=0.96))["level"] == "Red"


def test_ed_wait_time_levels():
    assert dept_alert(row(wait=35))["level"] == "Yellow"
    assert dept_alert(row(wait=50))["level"] == "Orange"
    assert dept_alert(row(wait=65))["level"] == "Red"


def test_highest_colour_wins():
    r = dept_alert(row(dept_id=3, occupancy=0.78, staff=60))
    assert r["level"] == "Red"
    assert "Staff availability 60.0%" in r["reasons"][0]


def test_staff_and_arrival_levels():
    assert staff_level(96) == 0
    assert staff_level(90) == 1
    assert staff_level(80) == 2
    assert staff_level(65) == 3
    assert arrivals_level(30) == 0
    assert arrivals_level(70) == 2


def test_capacity_level_zero_when_normal():
    rows = [row(dept_id=1), row(dept_id=2)]
    assert capacity_level(rows)["capacity_level"] == 0


def test_capacity_level_goes_up_with_ed_wait():
    assert capacity_level([row(dept_id=1, wait=35), row(dept_id=2)])["capacity_level"] == 1
    assert capacity_level([row(dept_id=1, wait=50), row(dept_id=2)])["capacity_level"] == 2
    assert capacity_level([row(dept_id=1, wait=65), row(dept_id=2)])["capacity_level"] == 3


def test_actions_are_given_for_level_two():
    result = capacity_level([row(dept_id=1, wait=50), row(dept_id=2)])
    assert len(result["actions"]) > 0
