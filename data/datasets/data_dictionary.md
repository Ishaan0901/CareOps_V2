# CareOps General Hospital - synthetic hourly dataset

Files: departments.csv (10 rows), hourly_metrics.csv (243,360 rows = 10 departments x 24,336 hours, 2024-01-01 to 2026-10-10).
Department beds and nurse ratios match the hospital PDFs (400 beds in total).

Columns of hourly_metrics.csv
- timestamp, department_id (join with departments.csv), hour, day_of_week (0 = Monday), month, is_weekend, is_holiday (26 Jan, 15 Aug, 2 Oct, 25 Dec)
- arrivals: new patients entering the unit in that hour (ED visits, or admissions for wards). Main prediction target.
- discharges: patients leaving the unit in that hour
- occupied_beds, total_beds, occupancy_rate
- nurses_scheduled, nurses_present, staff_availability_pct (present / scheduled x 100)
- patients_per_nurse (occupied_beds / nurses_present, compare with target_patients_per_nurse)
- avg_wait_min: average wait before first assessment (ED) or bed allocation (other units)
- alert_level: Green/Yellow/Orange/Red from the document thresholds. Label, not a feature.
- is_anomaly, anomaly_type (arrival_surge, outbreak, staff_shortage, none). Labels, not features.

Notes: data is synthetic. Do not use alert_level, is_anomaly or anomaly_type as model inputs. For arrivals prediction use only past values (lags) and calendar columns.
