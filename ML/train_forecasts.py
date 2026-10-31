"""Trains the forecast models: 3 metrics (arrivals, occupancy, wait) x 6 hours ahead.
One XGBoost model for each metric and each hour ahead.
Run once from the project folder:  python ML/train_forecasts.py
The models are saved in ML/saved_models and the test errors are printed."""
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error
from ml_tools import make_features

HERE = Path(__file__).resolve().parent
HORIZONS = range(1, 7)

df = pd.read_csv(HERE.parent / "data" / "datasets" / "hourly_metrics.csv", parse_dates=["timestamp"])
ed = df[df.department_id == 1].sort_values("timestamp").set_index("timestamp")
hosp = df.groupby("timestamp")[["occupied_beds", "total_beds"]].sum()
SERIES = {
    "arrivals": ed["arrivals"].astype(float),
    "occupancy": (hosp["occupied_beds"] * 100 / hosp["total_beds"]).sort_index(),
    "wait": ed["avg_wait_min"].astype(float),
}

if __name__ == "__main__":
    os.makedirs(HERE / "saved_models", exist_ok=True)
    for name, s in SERIES.items():
        vals, idx = s.values, s.index
        for h in HORIZONS:
            X, y = [], []
            for i in range(168, len(vals) - h):          # i = last known hour
                X.append(make_features(vals[: i + 1], idx[i], h)); y.append(vals[i + h])
            X = pd.DataFrame(X); y = np.array(y)
            cut = int(len(X) * 0.8)                      # last 20% of the time is kept for testing
            m = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
            m.fit(X[:cut], y[:cut])
            mae = mean_absolute_error(y[cut:], m.predict(X[cut:]))
            base = mean_absolute_error(y[cut:], X["same_hour_last_week"][cut:])   # compare: same hour last week
            print(f"{name:<9} +{h}h  model MAE {mae:6.2f}   baseline(last week) MAE {base:6.2f}")
            m.save_model(str(HERE / "saved_models" / f"forecast_{name}_h{h}.json"))   # json works on any xgboost version
            features = list(X.columns)
    json.dump(features, open(HERE / "saved_models" / "forecast_features.json", "w"))
