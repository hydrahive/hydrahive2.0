"""SQLite → PostgreSQL-Mirror Import.

Liest alle Sessions und Messages aus der SQLite-DB und schreibt fehlende Events
in den PG-Mirror. ON CONFLICT DO NOTHING — bereits vorhandene Events bleiben.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

_running: bool = False
_progress: dict[str, int] = {"sessions": 0, "messages": 0, "events": 0, "total_sessions": 0}


def sqlite_import_status() -> dict:
    return {"running": _running, **_progress}


async def run_sqlite_import() -> None:
    global _running, _progress
    if _running:
        return
    _running = True
    _progress = {"sessions": 0, "messages": 0, "events": 0, "total_sessions": 0}
    try:
        from hydrahive.db import mirror
        from hydrahive.settings import settings
        if not mirror._pool:
            raise RuntimeError("PG-Mirror nicht aktiv")

        db_path = str(settings.sessions_db)
        sessions = await asyncio.to_thread(_read_all_sessions, db_path)
        _progress["total_sessions"] = len(sessions)
        logger.info("SQLite-Import: %d Sessions", len(sessions))

        for s in sessions:
            messages = await asyncio.to_thread(_read_messages, db_path, s["id"])
            for m in messages:
                events = _explode_row(m, s)
                if events:
                    await _insert_events(mirror._pool, events)
                    _progress["events"] += len(events)
                _progress["messages"] += 1
            _progress["sessions"] += 1

        logger.info(
            "SQLite-Import abgeschlossen: %d Sessions, %d Messages, %d Events",
            _progress["sessions"], _progress["messages"], _progress["events"],
        )
    except Exception as e:
        logger.warning("SQLite-Import fehlgeschlagen: %s", e)
    finally:
        _running = False


def _read_all_sessions(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM sessions").fetchall()]
    finally:
        conn.close()


def _read_messages(db_path: str, session_id: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY created_at",
            (session_id,),
        ).fetchall()]
    finally:
        conn.close()


def _explode_row(m: dict, s: dict) -> list[dict]:
    from hydrahive.db.mirror import _explode, _parse_ts
    from hydrahive.db._message_model import Message
    from hydrahive.db.sessions import Session

    content = m.get("content", "")
    try:
        content = json.loads(content)
    except Exception:
        pass

    msg = Message(
        id=m["id"],
        session_id=m["session_id"],
        role=m["role"],
        content=content,
        created_at=m.get("created_at", ""),
        token_count=m.get("token_count"),
    )
    session = Session(
        id=s["id"],
        agent_id=s["agent_id"],
        user_id=s["user_id"],
        project_id=s.get("project_id"),
        title=s.get("title"),
        status=s.get("status", "active"),
        created_at=s.get("created_at", ""),
        updated_at=s.get("updated_at", ""),
    )
    return _explode(msg, session)


async def _insert_events(pool: Any, events: list[dict]) -> None:
    from hydrahive.db.mirror import _parse_ts
    try:
        async with pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO events (id, message_id, session_id, block_index,
                  chunk_index, chunk_total, username, agent_id, agent_name,
                  project_id, event_type, text, tool_name, tool_use_id,
                  tool_input, tool_output, is_error, token_count, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
                ON CONFLICT (id) DO NOTHING
            """, [
                (
                    e["id"], e["message_id"], e["session_id"], e["block_index"],
                    e["chunk_index"], e["chunk_total"], e["username"], e["agent_id"],
                    e["agent_name"], e["project_id"], e["event_type"], e.get("text"),
                    e.get("tool_name"), e.get("tool_use_id"),
                    json.dumps(e["tool_input"]) if e.get("tool_input") is not None else None,
                    e.get("tool_output"), e.get("is_error"), e.get("token_count"),
                    _parse_ts(e["created_at"]),
                )
                for e in events
            ])
    except Exception as e:
        logger.warning("Insert fehlgeschlagen: %s", e)
