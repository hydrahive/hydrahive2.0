"""Datamining-Spiegel holt beim Start nach, was beim Herunterfahren verloren ging (Task a11e9091).

Prod 07.10.: Drei Nachrichten (21:45, während des Neustarts) fehlten im Datamining („pool is closing“, kein
Retry). Beim Start werden die Nachrichten des Zeitfensters aus SQLite eingelesen und fehlende Events eingefügt
(ON CONFLICT DO NOTHING – Vorhandenes bleibt).
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from hydrahive.db import _mirror_catchup


def _db(tmp_path, rows):
    path = tmp_path / "sessions.db"
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE sessions (id TEXT PRIMARY KEY, agent_id TEXT, user_id TEXT, project_id TEXT, title TEXT,
                               status TEXT, created_at TEXT, updated_at TEXT, metadata TEXT);
        CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, created_at TEXT,
                               token_count INTEGER, metadata TEXT);
    """)
    c.execute("INSERT INTO sessions VALUES ('s1','a1','till',NULL,'T','active','2026-10-07T10:00:00+00:00',"
              "'2026-10-07T19:45:00+00:00',NULL)")
    for mid, ts, text in rows:
        c.execute("INSERT INTO messages VALUES (?,?,?,?,?,NULL,NULL)",
                  (mid, "s1", "assistant", json.dumps([{"type": "text", "text": text}]), ts))
    c.commit()
    c.close()
    return path


def _iso(dt):
    return dt.isoformat(timespec="milliseconds")


def test_only_messages_inside_window_are_reinserted(tmp_path, monkeypatch):
    now = datetime(2026, 10, 7, 19, 50, tzinfo=timezone.utc)
    path = _db(tmp_path, [("old", _iso(now - timedelta(hours=7)), "alt"),
                          ("new1", _iso(now - timedelta(minutes=5)), "neu eins"),
                          ("new2", _iso(now - timedelta(minutes=1)), "neu zwei")])
    inserted = []

    async def fake_insert(pool, events):
        inserted.extend(events)
        return len(events)
    monkeypatch.setattr(_mirror_catchup, "insert_events", fake_insert)
    n = asyncio.run(_mirror_catchup.catch_up(object(), str(path), hours=6, now=now))
    assert {e["message_id"] for e in inserted} == {"new1", "new2"}
    assert n == len(inserted) and all(e["session_id"] == "s1" and e["username"] == "till" for e in inserted)
    assert any(e.get("text") == "neu zwei" for e in inserted)


def test_without_pool_nothing_happens(tmp_path, monkeypatch):
    path = _db(tmp_path, [("m", _iso(datetime.now(timezone.utc)), "x")])
    monkeypatch.setattr(_mirror_catchup, "_read_window", lambda *a: (_ for _ in ()).throw(AssertionError("liest")))
    monkeypatch.setattr(_mirror_catchup.logger, "warning", lambda *a: (_ for _ in ()).throw(AssertionError("Fehlerpfad")))
    assert asyncio.run(_mirror_catchup.catch_up(None, str(path), hours=6)) == 0


def test_errors_are_logged_not_raised(tmp_path, monkeypatch, caplog):
    path = _db(tmp_path, [("m", _iso(datetime.now(timezone.utc)), "x")])

    async def boom(pool, events):
        raise RuntimeError("PG weg")
    monkeypatch.setattr(_mirror_catchup, "insert_events", boom)
    with caplog.at_level("WARNING"):
        assert asyncio.run(_mirror_catchup.catch_up(object(), str(path), hours=6)) == 0
    assert "nachziehen" in caplog.text.lower()


def test_missing_db_file_is_harmless_and_not_created(tmp_path):
    missing = tmp_path / "fehlt.db"
    assert _mirror_catchup._read_window(str(missing), "2026-01-01T00:00:00") == []
    assert not missing.exists()


def test_start_runs_catchup_in_background_and_is_tracked(monkeypatch):
    from hydrahive.db import _mirror_tasks
    monkeypatch.setattr(_mirror_tasks, "tasks", set())
    calls = []

    async def fake_catch_up(pool, db_path, hours):
        calls.append((pool, db_path, hours))
        await asyncio.sleep(0.01)
        return 0
    monkeypatch.setattr(_mirror_catchup, "catch_up", fake_catch_up)

    async def body():
        _mirror_catchup.start("POOL", "/x/sessions.db")
        tracked = len(_mirror_tasks.tasks)
        await asyncio.sleep(0.05)
        return tracked
    assert asyncio.run(body()) == 1
    assert calls == [("POOL", "/x/sessions.db", _mirror_catchup.CATCHUP_HOURS)]


def test_init_starts_catchup_after_pool_is_ready(monkeypatch):
    """mirror.init(): nach „PG-Mirror bereit“ wird das Nachziehen mit Pool + sessions.db gestartet."""
    from hydrahive.db import mirror
    src = __import__("inspect").getsource(mirror.init)
    assert src.index('logger.info("PG-Mirror bereit")') < src.index("_start_catchup(_pool, str(settings.sessions_db))")
