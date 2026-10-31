# Tests for the API. They need PostgreSQL running with the data loaded (python Backend/load_data.py).
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parent.parent / "Backend"))
from main import app

client = TestClient(app)


def test_summary_has_four_numbers():
    data = client.get("/api/summary").json()
    for key in ["occupancy", "wait", "arrivals", "staff"]:
        assert key in data


def test_ten_departments():
    assert len(client.get("/api/departments").json()["departments"]) == 10


def test_alerts_and_capacity_level():
    data = client.get("/api/alerts").json()
    assert data["capacity"]["level"] in [0, 1, 2, 3]
    assert len(data["alerts"]) > 0


def test_trend_for_every_metric():
    for metric in ["arrivals", "occupancy", "wait"]:
        data = client.get(f"/api/trend?metric={metric}&hours=24").json()
        assert len(data["past"]) == 24
        assert len(data["fc"]) == 6


def test_documents_and_pdf_download():
    docs = client.get("/api/documents").json()
    assert len(docs) == 11
    assert client.get("/docs/" + docs[0][1]).status_code == 200
