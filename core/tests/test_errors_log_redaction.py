"""errors_log schwärzt bekannte Secret-Werte in Meldung, Traceback und Kontext (Live-Fund 15.10.2026:
httpx-Fehler „Illegal header value b' sk-ant-oat01-…'“ landete mit vollem Token in der Datenbank)."""
from __future__ import annotations

import pytest

from hydrahive.db import errors_log, init_db

SECRET = "sk-ant-oat01-TESTGEHEIM-abcdefghijklmnopqrstuvwxyz0123456789"


@pytest.fixture(autouse=True)
def _ensure_db(setup_test_env, monkeypatch):
    init_db()
    from hydrahive.credentials import secret_sources
    monkeypatch.setattr(secret_sources, "secret_values", lambda: {SECRET})


def _row(eid):
    return next(r for r in errors_log.recent(limit=50) if r["id"] == eid)


def test_secret_in_exception_wird_geschwaerzt():
    try:
        raise ValueError(f"Illegal header value b' {SECRET}'")
    except ValueError as e:
        eid = errors_log.record(source="test.secret", exc=e, context={"header": SECRET})
    row = _row(eid)
    for feld in ("error_message", "traceback", "context"):
        assert SECRET not in (row[feld] or ""), feld
    assert "[REDACTED]" in row["error_message"]


def test_secret_in_verketteter_ursache_wird_geschwaerzt():
    try:
        try:
            raise RuntimeError(f"inner {SECRET}")
        except RuntimeError as inner:
            raise ConnectionError("Connection error.") from inner
    except ConnectionError as e:
        eid = errors_log.record(source="test.chain", exc=e)
    row = _row(eid)
    assert row["error_message"] == "Connection error."
    assert SECRET not in row["traceback"]


def test_ohne_secret_bleibt_alles_gleich():
    eid = errors_log.record(source="test.plain", message="ganz normal", context={"a": 1})
    row = _row(eid)
    assert row["error_message"] == "ganz normal" and '"a": 1' in row["context"]


def test_schwaerzung_kaputt_verliert_den_fehler_nicht(monkeypatch):
    from hydrahive.credentials import secret_sources

    def boom():
        raise OSError("llm.json weg")

    monkeypatch.setattr(secret_sources, "secret_values", boom)
    try:
        raise ValueError("trotzdem da")
    except ValueError as e:
        eid = errors_log.record(source="test.boom", exc=e, context={"header": SECRET})
    row = _row(eid)
    assert row["error_message"] == "trotzdem da"
    assert row["traceback"] is None and row["context"] is None, "ungeschwärzt nichts Zusätzliches speichern"
