"""Mirror — Such-Funktionen (Volltext + semantisch) und embed_status."""
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


def _pool():
    from hydrahive.db import mirror
    return mirror._pool


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
                          AND (nullif(text,'') IS NOT NULL OR nullif(tool_output,'') IS NOT NULL OR nullif(tool_input::text,'') IS NOT NULL)
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
               round((1 - (embedding <=> $1::vector))::numeric, 3)::float8 AS similarity
        FROM events
        WHERE {' AND '.join(where)}
        ORDER BY embedding <=> $1::vector
        LIMIT ${idx}
    """, *params)
    return [dict(r) for r in rows]
