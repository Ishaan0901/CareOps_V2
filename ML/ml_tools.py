"""ML helper functions used by the AI agent and the dashboard backend.

detect_anomaly(hour, day_of_week, arrivals)
    Is this hour's ED arrivals unusually high?
predict_arrivals(history, timestamp)
    Forecast of ED arrivals for the next hour.

The trained files are loaded from the saved_models folder next to this file.
"""
import os

import joblib
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')

# (month, day): Republic Day, Independence Day, Gandhi Jayanti, Christmas
HOLIDAYS = {(1, 26), (8, 15), (10, 2), (12, 25)}

# The model needs the last 168 hours (one week) for its lag features.
HISTORY_HOURS = 168

_anomaly_rule = joblib.load(os.path.join(MODEL_DIR, 'anomaly_rule.joblib'))
_arrivals_model = joblib.load(os.path.join(MODEL_DIR, 'arrivals_model.joblib'))
_feature_names = joblib.load(os.path.join(MODEL_DIR, 'arrivals_features.joblib'))


def detect_anomaly(hour, day_of_week, arrivals):
    """Compare arrivals with the usual arrivals for the same hour and day of week.

    hour: 0 to 23. day_of_week: 0 = Monday to 6 = Sunday. arrivals: patients that hour.
    Returns {'is_anomaly': bool, 'z_score': float, 'usual_arrivals': float}.
    """
    usual = _anomaly_rule['usual']
    row = usual[(usual['hour'] == hour) & (usual['day_of_week'] == day_of_week)].iloc[0]
    z_score = (arrivals - row['mean']) / row['std']
    return {
        'is_anomaly': bool(z_score > _anomaly_rule['threshold']),
        'z_score': round(float(z_score), 2),
        'usual_arrivals': round(float(row['mean']), 1),
    }


def predict_arrivals(history, timestamp):
    """Forecast ED arrivals for the hour that starts at `timestamp`.

    history: DataFrame of the hours before it, oldest first, at least 168 rows,
             with columns arrivals, occupancy_rate, avg_wait_min, staff_availability_pct.
    timestamp: the hour to predict.
    Returns the predicted number of arrivals.
    """
    if len(history) < HISTORY_HOURS:
        raise ValueError(f'history needs at least {HISTORY_HOURS} rows, got {len(history)}')

    ts = pd.Timestamp(timestamp)
    arrivals = history['arrivals'].values
    last = history.iloc[-1]

    features = {
        'hour': ts.hour,
        'day_of_week': ts.dayofweek,
        'month': ts.month,
        'is_weekend': int(ts.dayofweek >= 5),
        'is_holiday': int((ts.month, ts.day) in HOLIDAYS),
        'lag_1': arrivals[-1],
        'lag_24': arrivals[-24],
        'lag_168': arrivals[-168],
        'roll_mean_6': arrivals[-6:].mean(),
        'roll_mean_24': arrivals[-24:].mean(),
        'occupancy_rate_lag1': last['occupancy_rate'],
        'avg_wait_min_lag1': last['avg_wait_min'],
        'staff_availability_pct_lag1': last['staff_availability_pct'],
    }
    x = pd.DataFrame([features])[_feature_names]
    return round(float(_arrivals_model.predict(x)[0]), 1)
