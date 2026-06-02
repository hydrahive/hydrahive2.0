"""#208 (Befunde M1/M1c): stille Import-Fehler werden geloggt + der
Health-Live-Ingest ist atomar (Roh-Insert + Tages-Rollup in EINER Transaktion).
"""
from __future__ import annotations

import logging

import pytest

from hydrahive.db import ega as ega_db
from hydrahive.db import fhir as fhir_db
from hydrahive.db import health as health_db


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    init_db()
    yield
    with db() as conn:
        for tbl in ("ega_records", "fhir_resources", "health_ingest", "health_daily"):
            conn.execute(f"DELETE FROM {tbl}")


# --- M1a: ega.upsert_records loggt verschluckte Fehler statt still zu zählen --

def test_ega_upsert_logs_swallowed_error(caplog):
    # set ist nicht JSON-serialisierbar → wirft im try-Block, wird verschluckt
    records = [("Medikament", {"boom": {1, 2}})]
    with caplog.at_level(logging.WARNING, logger="hydrahive.db.ega"):
        result = ega_db.upsert_records(records, "u_ega")
    assert result["errors"] == 1
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


# --- M1b: fhir.upsert_bundle loggt verschluckte Fehler -----------------------

def test_fhir_upsert_logs_swallowed_error(caplog):
    bundle = {
        "resourceType": "Bundle",
        "entry": [{"resource": {"resourceType": "Observation", "id": "1", "boom": {1, 2}}}],
    }
    with caplog.at_level(logging.WARNING, logger="hydrahive.db.fhir"):
        result = fhir_db.upsert_bundle(bundle, "u_fhir")
    assert result["errors"] == 1
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


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
