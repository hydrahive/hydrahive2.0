"""Datamining-Spiegel: beim Start fehlende Events der letzten Stunden aus SQLite nachziehen (Task a11e9091).

Der Spiegel schreibt „fire-and-forget“ ohne Wiederholung. Beim Herunterfahren abgebrochene oder gegen den
schließenden Pool gelaufene Schreibvorgänge fehlten deshalb dauerhaft im Datamining (Prod 07.10.: 3 Nachrichten).
Einmal nach dem Start werden die Nachrichten des Zeitfensters gelesen und ihre Events eingefügt
(``ON CONFLICT DO NOTHING`` – Vorhandenes bleibt, nur Lücken werden gefüllt). Embeddings der neuen Events holt der
normale Weg bzw. der Backfill. Fehler werden geloggt, nie geworfen (Start darf nicht scheitern).
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hydrahive.db import _mirror_tasks
from hydrahive.db.mirror_import_sqlite import _explode_row, _insert_events

logger = logging.getLogger(__name__)

CATCHUP_HOURS = 6


async def insert_events(pool, events: list[dict]) -> int:
    await _insert_events(pool, events)
    return len(events)


def _read_window(db_path: str, since: str) -> list[tuple[dict, dict]]:
    if not Path(db_path).is_file():
        return []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT m.*, s.agent_id AS s_agent_id, s.user_id AS s_user_id, s.project_id AS s_project_id, "
            "s.title AS s_title, s.status AS s_status, s.created_at AS s_created_at, s.updated_at AS s_updated_at "
            "FROM messages m JOIN sessions s ON s.id = m.session_id WHERE m.created_at >= ? ORDER BY m.created_at",
            (since,)).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        r = dict(r)
        session = {"id": r["session_id"], "agent_id": r["s_agent_id"], "user_id": r["s_user_id"],
                   "project_id": r["s_project_id"], "title": r["s_title"], "status": r["s_status"],
                   "created_at": r["s_created_at"], "updated_at": r["s_updated_at"]}
        out.append(({k: v for k, v in r.items() if not k.startswith("s_")}, session))
    return out


async def catch_up(pool, db_path: str, hours: int = CATCHUP_HOURS, *, now: datetime | None = None) -> int:
    """Events aller Nachrichten der letzten ``hours`` Stunden einfügen. Rückgabe: Zahl übergebener Events."""
    if pool is None:
        return 0
    since = ((now or datetime.now(timezone.utc)) - timedelta(hours=hours)).isoformat(timespec="seconds")
    try:
        pairs = await asyncio.to_thread(_read_window, db_path, since)
        events = [e for m, s in pairs for e in _explode_row(m, s)]
        if not events:
            return 0
        n = await insert_events(pool, events)
        logger.info("PG-Mirror: %d Events der letzten %d h nachgezogen (fehlende ergänzt)", n, hours)
        return n
    except Exception as e:  # noqa: BLE001 — Start darf am Nachziehen nicht scheitern
        logger.warning("PG-Mirror: Nachziehen der letzten %d h fehlgeschlagen: %s", hours, e)
        return 0


def start(pool, db_path: str) -> None:
    """Im Hintergrund nachziehen – verfolgt, damit ein Herunterfahren es begrenzt abbricht."""
    try:
        _mirror_tasks.track(catch_up(pool, db_path, CATCHUP_HOURS))
    except RuntimeError as e:
        logger.warning("PG-Mirror: Nachziehen nicht gestartet (kein Event-Loop): %s", e)
