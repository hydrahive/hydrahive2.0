"""Health-Ingest-Logging + Atomarität.

Portiert beim Apple-Health-Modul-Port aus core test_db_import_logging (#208 M1c)
+ test_logging_hardening (#203). db.health lebt jetzt als Modul-health_store.
"""
from __future__ import annotations

import logging

import pytest

from backend import health_store as health


def _insert_raw_ingest(user_id: str, payload_text: str) -> None:
    from hydrahive.db._utils import now_iso, uuid7
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute(
            """INSERT INTO health_ingest
               (id, received_at, user_id, automation_name, automation_id,
                session_id, period, aggregation, payload)
               VALUES (?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?)""",
            (uuid7(), now_iso(), user_id, payload_text),
        )


# --- #208 M1c: insert loggt unverarbeitbare Payload + ist atomar -------------

def test_health_insert_logs_unprocessable_payload(caplog):
    with caplog.at_level(logging.WARNING, logger="backend.health_store"):
        rid = health.insert({"data": "kein-dict"}, "u_health")
    assert rid
    assert health.list_recent("u_health")  # Rohsatz bleibt gespeichert
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_health_insert_atomic_on_rollup_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rollup boom")

    monkeypatch.setattr(health, "_aggregate_samples", boom)
    payload = {"data": {"metrics": [
        {"name": "step_count", "units": "count", "data": [{"date": "2026-06-01", "qty": 100}]},
    ]}}
    with pytest.raises(RuntimeError):
        health.insert(payload, "u_atomic")
    # Eine Transaktion → Rollup-Fehler rollt auch den Roh-Insert zurück.
    assert health.list_recent("u_atomic") == []


# --- #203: backfill_daily loggt beide except-Zweige -------------------------

def test_backfill_logs_invalid_json_and_continues(caplog):
    _insert_raw_ingest("hjson", "{ this is not valid json")
    with caplog.at_level(logging.WARNING):
        count = health.backfill_daily("hjson")
    assert count == 0
    assert any("ungültiger JSON" in r.message for r in caplog.records)


def test_backfill_logs_processing_error(caplog, monkeypatch):
    _insert_raw_ingest("hproc", '{"ok": true}')

    def _boom(payload, user_id, conn):
        raise ValueError("db kaputt")

    monkeypatch.setattr(health, "_process_payload_to_daily", _boom)
    with caplog.at_level(logging.ERROR):
        count = health.backfill_daily("hproc")
    assert count == 0
    assert any("Row-Verarbeitung fehlgeschlagen" in r.message for r in caplog.records)
