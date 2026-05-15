"""Tests für Health DB + API Metrics-Endpunkt."""
from __future__ import annotations
import pytest
from hydrahive.db import health as health_db
from hydrahive.db import init_db


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    """Ensure DB schema is initialized before each test."""
    init_db()


def _insert_payload(metrics: list[dict], days_ago: int = 0) -> str:
    from datetime import datetime, timezone, timedelta
    from hydrahive.db._utils import uuid7
    from hydrahive.db.connection import db
    import json as _json

    received = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    payload = {"data": {"metrics": metrics, "workouts": []}}
    record_id = uuid7()
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, automation_name, automation_id, session_id, period, aggregation, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_id, received, "Test", "test-id", "sess", "Default", "Default",
             _json.dumps(payload)),
        )
    return record_id


def test_get_metrics_summary_leer():
    result = health_db.get_metrics_summary(days=7)
    assert "metrics" in result
    assert "last_ingest" in result
    assert result["metrics"] == {}


def test_get_metrics_summary_schritte_summiert():
    _insert_payload([
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-05-15 00:00:00 +0200", "qty": 5000}]}
    ], days_ago=0)
    _insert_payload([
        {"name": "step_count", "units": "count",
         "data": [{"date": "2026-05-15 12:00:00 +0200", "qty": 3000}]}
    ], days_ago=0)
    result = health_db.get_metrics_summary(days=7)
    step = result["metrics"].get("step_count")
    assert step is not None
    assert step["latest"] == 8000  # summiert
    assert step["unit"] == "count"


def test_get_metrics_summary_herzfrequenz_gemittelt():
    _insert_payload([
        {"name": "heart_rate", "units": "bpm",
         "data": [
             {"date": "2026-05-15 08:00:00 +0200", "qty": 60},
             {"date": "2026-05-15 12:00:00 +0200", "qty": 80},
         ]}
    ], days_ago=0)
    result = health_db.get_metrics_summary(days=7)
    hr = result["metrics"].get("heart_rate")
    assert hr is not None
    assert hr["latest"] == 70  # Mittelwert
    assert hr["unit"] == "bpm"


def test_get_metrics_summary_metric_filter():
    result = health_db.get_metrics_summary(days=7, metric="step_count")
    for key in result["metrics"]:
        assert key == "step_count"
