"""PostgreSQL Datamining — Lese-Seite (Search, Sessions, Session-Detail)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _dt(s: str) -> datetime:
    """Parst ISO-Datum/-Datetime zu timezone-aware datetime für asyncpg."""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.fromisoformat(s + "T00:00:00")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def embed_status() -> dict:
    from hydrahive.db import mirror
    from hydrahive.llm._config import load_config
    pool = mirror._pool
    if not pool:
        return {"active": False, "total": 0, "embedded": 0, "pending": 0, "model": "", "backfill_running": False}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(embedding)::int AS embedded,
                    COUNT(*) FILTER (
                        WHERE embedding IS NULL
                          AND (text IS NOT NULL OR tool_output IS NOT NULL OR tool_input IS NOT NULL)
                    )::int AS pending
                FROM events
            """)
        model = load_config().get("embed_model", "")
        return {
            "active": True,
            "total": row["total"],
            "embedded": row["embedded"],
            "pending": row["pending"],
            "model": model,
            "backfill_running": mirror._backfill_running,
        }
    except Exception as e:
        logger.warning("embed_status fehlgeschlagen: %s", e)
        return {"active": False, "total": 0, "embedded": 0, "pending": 0, "model": "", "backfill_running": False}


def _pool():
    from hydrahive.db import mirror
    return mirror._pool


async def search_events(
    q: str,
    *,
    event_type: str | None = None,
    agent_name: str | None = None,
    username: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    semantic: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    pool = _pool()
    if not pool:
        return []
    try:
        async with pool.acquire() as conn:
            if semantic:
                return await _semantic_search(conn, q, event_type, agent_name, username, from_date, to_date, limit)
            return await _text_search(conn, q, event_type, agent_name, username, from_date, to_date, limit)
    except Exception as e:
        logger.warning("search_events fehlgeschlagen: %s", e)
        raise


async def _text_search(conn, q, event_type, agent_name, username, from_date, to_date, limit):
    pat = f"%{q}%"
    where = ["(text ILIKE $1 OR tool_output ILIKE $1 OR tool_input::text ILIKE $1 OR tool_name ILIKE $1)"]
    params: list = [pat]
    idx = 2

    if event_type:
        where.append(f"event_type = ${idx}"); params.append(event_type); idx += 1
    if agent_name:
        where.append(f"agent_name = ${idx}"); params.append(agent_name); idx += 1
    if username:
        where.append(f"username = ${idx}"); params.append(username); idx += 1
    if from_date:
        where.append(f"created_at >= ${idx}"); params.append(_dt(from_date)); idx += 1
    if to_date:
        where.append(f"created_at <= ${idx}"); params.append(_dt(to_date)); idx += 1
    params.append(limit)

    rows = await conn.fetch(f"""
        SELECT id, session_id, username, agent_name, event_type, created_at,
               tool_name, is_error,
               left(coalesce(text, tool_output, tool_input::text, ''), 300) AS snippet
        FROM events
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT ${idx}
    """, *params)
    return [dict(r) for r in rows]


async def _semantic_search(conn, q, event_type, agent_name, username, from_date, to_date, limit):
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import aembed

    model = load_config().get("embed_model", "")
    if not model:
        raise ValueError("Kein Embedding-Modell konfiguriert")
    vec = await aembed(q, model)
    if vec is None:
        raise ValueError("Embedding fehlgeschlagen")

    vec_str = "[" + ",".join(str(x) for x in vec) + "]"
    where = ["embedding IS NOT NULL"]
    params: list = [vec_str]
    idx = 2

    if event_type:
        where.append(f"event_type = ${idx}"); params.append(event_type); idx += 1
    if agent_name:
        where.append(f"agent_name = ${idx}"); params.append(agent_name); idx += 1
    if username:
        where.append(f"username = ${idx}"); params.append(username); idx += 1
    if from_date:
        where.append(f"created_at >= ${idx}"); params.append(_dt(from_date)); idx += 1
    if to_date:
        where.append(f"created_at <= ${idx}"); params.append(_dt(to_date)); idx += 1
    params.append(limit)

    rows = await conn.fetch(f"""
        SELECT id, session_id, username, agent_name, event_type, created_at,
               tool_name, is_error,
               left(coalesce(text, tool_output, ''), 300) AS snippet,
               round((1 - (embedding <=> $1::vector))::numeric, 3) AS similarity
        FROM events
        WHERE {' AND '.join(where)}
        ORDER BY embedding <=> $1::vector
        LIMIT ${idx}
    """, *params)
    return [dict(r) for r in rows]


async def list_sessions(
    agent_name: str | None = None,
    username: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    pool = _pool()
    if not pool:
        return []

    where = ["1=1"]
    params: list = []
    idx = 1

    if agent_name:
        where.append(f"s.agent_name = ${idx}"); params.append(agent_name); idx += 1
    if username:
        where.append(f"s.username = ${idx}"); params.append(username); idx += 1
    params.append(min(limit, 200))

    # Filter für Events-Query neu aufbauen (gleiche Parameter, andere Spaltennamen)
    where_e = ["1=1"]
    params_e: list = []
    idx_e = 1
    if agent_name:
        where_e.append(f"agent_name = ${idx_e}"); params_e.append(agent_name); idx_e += 1
    if username:
        where_e.append(f"username = ${idx_e}"); params_e.append(username); idx_e += 1
    params_e.append(min(limit, 200))

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT
                    session_id                 AS id,
                    MAX(username)              AS username,
                    MAX(agent_name)            AS agent_name,
                    MAX(project_id)            AS project_id,
                    NULL::text                 AS title,
                    'active'                   AS status,
                    MIN(created_at)            AS started_at,
                    MAX(created_at)            AS updated_at,
                    COUNT(*)::int              AS event_count
                FROM events
                WHERE {' AND '.join(where_e)}
                GROUP BY session_id
                ORDER BY MAX(created_at) DESC
                LIMIT ${idx_e}
            """, *params_e)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("list_sessions fehlgeschlagen: %s", e)
        return []


async def get_session_detail(session_id: str) -> dict[str, Any] | None:
    pool = _pool()
    if not pool:
        return None

    try:
        async with pool.acquire() as conn:
            meta = await conn.fetchrow("""
                SELECT id, username, agent_name, project_id, title, status,
                       started_at, updated_at
                FROM sessions WHERE id = $1
            """, session_id)
            if not meta:
                return None

            rows = await conn.fetch("""
                SELECT message_id, block_index, chunk_index, chunk_total,
                       event_type, created_at, username, agent_name,
                       tool_name, tool_use_id, tool_input, is_error,
                       text, tool_output
                FROM events
                WHERE session_id = $1
                ORDER BY created_at, block_index, chunk_index
            """, session_id)

            return {
                "session": dict(meta),
                "events": _merge_chunks([dict(r) for r in rows]),
            }
    except Exception as e:
        logger.warning("get_session_detail fehlgeschlagen: %s", e)
        return None


def _merge_chunks(rows: list[dict]) -> list[dict]:
    merged: list[dict] = []
    buf: dict | None = None

    for r in rows:
        key = (r["message_id"], r["block_index"])
        if buf is None or buf["_key"] != key:
            if buf:
                merged.append(_finalize(buf))
            buf = {
                "_key": key,
                "event_type": r["event_type"],
                "created_at": str(r["created_at"]),
                "username": r["username"],
                "agent_name": r["agent_name"],
                "tool_name": r["tool_name"],
                "tool_use_id": r["tool_use_id"],
                "tool_input": r["tool_input"],
                "is_error": r["is_error"],
                "_text": [r["text"]] if r["text"] else [],
                "_output": [r["tool_output"]] if r["tool_output"] else [],
            }
        else:
            if r["tool_output"]:
                buf["_output"].append(r["tool_output"])
            if r["text"]:
                buf["_text"].append(r["text"])

    if buf:
        merged.append(_finalize(buf))
    return merged


def _finalize(buf: dict) -> dict:
    out = {k: v for k, v in buf.items() if not k.startswith("_")}
    text = "\n".join(p for p in buf["_text"] if p)
    output = "\n".join(p for p in buf["_output"] if p)
    if text:
        out["text"] = text
    if output:
        out["tool_output"] = output
    return out
