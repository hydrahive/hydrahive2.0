"""Token-Verbrauchs-Auswertung auf Session-Ebene.

Liest messages.metadata (JSON) das der Runner pro Turn befüllt:
  {"input_tokens": N, "output_tokens": N, "cache_creation_tokens": N, "cache_read_tokens": N}

Aggregierte Auswertungen (Zeitreihen, Agent-Übersichten) → token_stats_agg.py
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db.connection import db
from hydrahive.db.token_stats_agg import agent_stats, daily_stats  # noqa: F401


def session_stats(session_id: str) -> dict[str, Any] | None:
    with db() as conn:
        sess = conn.execute(
            "SELECT id, agent_id, user_id, title, created_at, updated_at, status FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not sess:
            return None

        rows = conn.execute(
            "SELECT role, token_count, metadata FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()

    input_tokens = output_tokens = cache_creation = cache_read = 0
    tool_call_count = compaction_count = message_count = 0

    for r in rows:
        message_count += 1
        meta = json.loads(r["metadata"]) if r["metadata"] else {}
        input_tokens     += meta.get("input_tokens", 0)
        output_tokens    += meta.get("output_tokens", 0)
        cache_creation   += meta.get("cache_creation_tokens", 0)
        cache_read       += meta.get("cache_read_tokens", 0)
        if meta.get("tool_calls"):
            tool_call_count += int(meta["tool_calls"])
        if meta.get("compaction"):
            compaction_count += 1

    total_prompt = input_tokens + cache_creation + cache_read
    cache_hit_pct = round(cache_read / total_prompt * 100, 1) if total_prompt else 0.0

    return {
        "session_id": session_id,
        "title": sess["title"],
        "agent_id": sess["agent_id"],
        "status": sess["status"],
        "created_at": sess["created_at"],
        "updated_at": sess["updated_at"],
        "message_count": message_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation,
        "cache_read_tokens": cache_read,
        "cache_hit_pct": cache_hit_pct,
        "tool_call_count": tool_call_count,
        "compaction_count": compaction_count,
    }


def latest_sessions(count: int = 5) -> list[dict[str, Any]]:
    """Letzte N Sessions mit Token-Kurzstats — für den Daily-Stand."""
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.agent_id, s.user_id, s.title, s.status, s.updated_at,
                   COUNT(m.id) AS message_count,
                   COALESCE(SUM(m.token_count), 0) AS output_tokens,
                   COALESCE(SUM(CAST(json_extract(m.metadata, '$.input_tokens') AS INTEGER)), 0) AS input_tokens,
                   COALESCE(SUM(CAST(json_extract(m.metadata, '$.cache_creation_tokens') AS INTEGER)), 0) AS cache_creation,
                   COALESCE(SUM(CAST(json_extract(m.metadata, '$.cache_read_tokens') AS INTEGER)), 0) AS cache_read
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (min(count, 100),),
        ).fetchall()

    result = []
    for r in rows:
        total_prompt = r["input_tokens"] + r["cache_creation"] + r["cache_read"]
        result.append({
            "session_id": r["id"],
            "agent_id": r["agent_id"],
            "user_id": r["user_id"],
            "title": r["title"],
            "status": r["status"],
            "updated_at": r["updated_at"],
            "message_count": r["message_count"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cache_read_tokens": r["cache_read"],
            "cache_hit_pct": round(r["cache_read"] / total_prompt * 100, 1) if total_prompt else 0.0,
        })
    return result
