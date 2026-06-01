"""Logging statt stillem Verschlucken (Issue #203, #204).

Best-effort-Pfade dürfen Fehler nicht lautlos schlucken — sonst sind operative
Blindspots nicht diagnostizierbar.

Hinweis: hydrahive-Imports bewusst LAZY in den Tests. Modul-Level-Import von
llm._oauth_usage würde settings.data_dir bereits zur Collection-Zeit (vor dem
setup_test_env-Fixture) einfrieren und damit die ganze Session vergiften.
"""
from __future__ import annotations

import logging


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


# --- #203 health.backfill_daily: beide except-Zweige loggen -----------------

def test_backfill_logs_invalid_json_and_continues(client, caplog):
    from hydrahive.db import health
    _insert_raw_ingest("hjson", "{ this is not valid json")
    with caplog.at_level(logging.WARNING):
        count = health.backfill_daily("hjson")
    assert count == 0
    assert any("ungültiger JSON" in r.message for r in caplog.records)


def test_backfill_logs_processing_error(client, caplog, monkeypatch):
    from hydrahive.db import health
    _insert_raw_ingest("hproc", '{"ok": true}')

    def _boom(payload, user_id):
        raise ValueError("db kaputt")

    monkeypatch.setattr(health, "_process_payload_to_daily", _boom)
    with caplog.at_level(logging.ERROR):
        count = health.backfill_daily("hproc")
    assert count == 0
    assert any("Row-Verarbeitung fehlgeschlagen" in r.message for r in caplog.records)


# --- #204 oauth_usage cache: load/save loggen statt schlucken ----------------

def test_oauth_load_cache_logs_on_corrupt_file(client, tmp_path, monkeypatch, caplog):
    from hydrahive.llm import _oauth_usage
    bad = tmp_path / "oauth_usage.json"
    bad.write_text("{ corrupt", encoding="utf-8")
    monkeypatch.setattr(_oauth_usage, "_CACHE_FILE", bad)
    with caplog.at_level(logging.WARNING):
        result = _oauth_usage._load_cache()
    assert result == {}
    assert any("laden fehlgeschlagen" in r.message for r in caplog.records)


def test_oauth_save_cache_logs_on_write_error(client, tmp_path, monkeypatch, caplog):
    from hydrahive.llm import _oauth_usage
    # Ziel ist ein Verzeichnis → write_text wirft IsADirectoryError
    monkeypatch.setattr(_oauth_usage, "_CACHE_FILE", tmp_path)
    with caplog.at_level(logging.WARNING):
        _oauth_usage._save_cache({"x": 1})  # darf NICHT werfen
    assert any("schreiben fehlgeschlagen" in r.message for r in caplog.records)
