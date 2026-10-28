-- CareOps AI tables (run once in pgAdmin on database careops)
CREATE TABLE departments (
  department_id INT PRIMARY KEY,
  department VARCHAR(60) NOT NULL,
  unit_type VARCHAR(30),
  licensed_beds INT NOT NULL,
  target_patients_per_nurse INT NOT NULL
);

CREATE TABLE hourly_metrics (
  timestamp TIMESTAMP NOT NULL,
  department_id INT REFERENCES departments(department_id),
  hour INT, day_of_week INT, month INT,
  is_weekend INT, is_holiday INT,
  arrivals INT, discharges INT,
  occupied_beds INT, total_beds INT, occupancy_rate NUMERIC,
  nurses_scheduled INT, nurses_present INT,
  staff_availability_pct NUMERIC, patients_per_nurse NUMERIC,
  avg_wait_min NUMERIC,
  alert_level VARCHAR(10),
  is_anomaly INT, anomaly_type VARCHAR(30),
  PRIMARY KEY (timestamp, department_id)
);

CREATE TABLE alerts (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW(),
  department_id INT REFERENCES departments(department_id),
  level VARCHAR(10) NOT NULL,
  capacity_level INT,
  message TEXT,
  source VARCHAR(20)  -- 'policy' or 'ml'
);
