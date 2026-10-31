# Loads the CSV data into PostgreSQL. It clears the old rows first, so it can be run again.
from pathlib import Path
import pandas as pd
from sqlalchemy import text
import services

base = Path(__file__).resolve().parent.parent / "data" / "datasets"
with services.engine.begin() as c:
    c.execute(text("TRUNCATE hourly_metrics, departments CASCADE"))

pd.read_csv(base / "departments.csv").to_sql("departments", services.engine, if_exists="append", index=False)
hm = pd.read_csv(base / "hourly_metrics.csv", parse_dates=["timestamp"])
hm.to_sql("hourly_metrics", services.engine, if_exists="append", index=False, chunksize=5000, method="multi")

with services.engine.connect() as c:
    print("departments:", c.execute(text("select count(*) from departments")).scalar())
    print("hourly_metrics:", c.execute(text("select count(*) from hourly_metrics")).scalar())
