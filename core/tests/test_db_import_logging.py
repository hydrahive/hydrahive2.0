"""#208 (Befund M1c): der Health-Live-Ingest loggt unverarbeitbare Payloads
und ist atomar (Roh-Insert + Tages-Rollup in EINER Transaktion).

Die eGA/FHIR-Import-Logging-Tests (M1a/M1b) leben seit dem Akte-Modul-Port
im Modul (modules/patientenakte/tests/test_import_logging.py).
"""
from __future__ import annotations

import logging

import pytest

from hydrahive.db import health as health_db


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    init_db()
    yield
    with db() as conn:
        for tbl in ("health_ingest", "health_daily"):
            conn.execute(f"DELETE FROM {tbl}")


# --- M1c (1): health-Ingest loggt unverarbeitbare Payload --------------------

def test_health_insert_logs_unprocessable_payload(caplog):
    with caplog.at_level(logging.WARNING, logger="hydrahive.db.health"):
        rid = health_db.insert({"data": "kein-dict"}, "u_health")
    assert rid
    assert health_db.list_recent("u_health")  # Rohsatz bleibt gespeichert
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


# --- M1c (2): Roh-Insert + Rollup sind atomar --------------------------------

def test_health_insert_atomic_on_rollup_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rollup boom")

    monkeypatch.setattr(health_db, "_aggregate_samples", boom)
    payload = {"data": {"metrics": [
        {"name": "step_count", "units": "count", "data": [{"date": "2026-06-01", "qty": 100}]},
    ]}}
    with pytest.raises(RuntimeError):
        health_db.insert(payload, "u_atomic")
    # Eine Transaktion → Rollup-Fehler rollt auch den Roh-Insert zurück.
    assert health_db.list_recent("u_atomic") == []
