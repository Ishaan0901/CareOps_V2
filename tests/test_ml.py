# Tests for the ML helper functions
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent / "ML"))
import ml_tools

LAST_TIME = pd.Timestamp("2026-10-10 23:00")


def test_anomaly_detected_for_big_spike():
    assert ml_tools.detect_anomaly(10, 2, 200)["is_anomaly"] is True


def test_normal_arrivals_are_not_anomaly():
    usual = ml_tools.detect_anomaly(10, 2, 0)["usual_arrivals"]
    assert ml_tools.detect_anomaly(10, 2, int(usual))["is_anomaly"] is False


def test_forecast_gives_six_hours_for_each_metric():
    values = np.full(168, 20.0)
    for metric in ["arrivals", "occupancy", "wait"]:
        result = ml_tools.forecast(metric, values, LAST_TIME)
        assert len(result) == 6
        assert result[0]["hour"] == pd.Timestamp("2026-10-11 00:00")


def test_occupancy_forecast_stays_between_0_and_100():
    values = np.full(168, 99.0)
    for item in ml_tools.forecast("occupancy", values, LAST_TIME):
        assert 0 <= item["value"] <= 100
