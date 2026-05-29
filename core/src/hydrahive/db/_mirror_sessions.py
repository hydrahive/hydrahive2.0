"""Mirror — Session-Listings + Detail-Abruf mit Chunk-Merging."""
from __future__ import annotations

import logging
from typing import Any

from hydrahive.db._mirror_search import _dt, _pool

logger = logging.getLogger(__name__)


async def list_sessions(
    agent_name: str | None = None,
    username: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    pool = _pool()
    if not pool:
        return []

    where_e = ["1=1"]
    params_e: list = []
    idx_e = 1

    if agent_name:
        where_e.append(f"agent_name = ${idx_e}"); params_e.append(agent_name); idx_e += 1
    if username:
        where_e.append(f"username = ${idx_e}"); params_e.append(username); idx_e += 1
    if from_date:
        where_e.append(f"created_at >= ${idx_e}"); params_e.append(_dt(from_date)); idx_e += 1
    if to_date:
        where_e.append(f"created_at <= ${idx_e}"); params_e.append(_dt(to_date)); idx_e += 1
    params_e.append(min(limit, 500))

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


async def event_type_counts(session_id: str) -> dict[str, int]:
    """{event_type: count} für eine Session — Input für derive_groundedness
    (Groundedness-Heuristik des proaktiven Recall: tool_result=belegt vs
    assistant_text=Behauptung). Siehe db/_mirror_cards_model.derive_groundedness."""
    pool = _pool()
    if not pool:
        return {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT event_type, COUNT(*)::int AS n FROM events "
                "WHERE session_id = $1 GROUP BY event_type",
                session_id,
            )
        return {r["event_type"]: r["n"] for r in rows}
    except Exception as e:
        logger.warning("event_type_counts fehlgeschlagen: %s", e)
        return {}


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
                meta = await conn.fetchrow("""
                    SELECT session_id AS id, MAX(username) AS username,
                           MAX(agent_name) AS agent_name, MAX(project_id) AS project_id,
                           NULL::text AS title, 'active' AS status,
                           MIN(created_at) AS started_at, MAX(created_at) AS updated_at
                    FROM events WHERE session_id = $1
                    GROUP BY session_id
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
