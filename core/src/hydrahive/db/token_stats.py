"""Token-Verbrauchs-Auswertung aus der SQLite-Sessions-DB.

Liest messages.metadata (JSON) das der Runner pro Turn befüllt:
  {"input_tokens": N, "output_tokens": N, "cache_creation_tokens": N, "cache_read_tokens": N}
"""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db.connection import db


def session_stats(session_id: str) -> dict[str, Any] | None:
    with db() as conn:
        # Session existiert?
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


def agent_stats(agent_id: str, days: int = 7) -> dict[str, Any]:
    with db() as conn:
        sessions = conn.execute(
            """
            SELECT id FROM sessions
            WHERE agent_id = ?
              AND updated_at >= datetime('now', ?)
            ORDER BY updated_at DESC
            """,
            (agent_id, f"-{days} days"),
        ).fetchall()

        if not sessions:
            return {
                "agent_id": agent_id, "days": days, "session_count": 0,
                "total_input_tokens": 0, "total_output_tokens": 0,
                "total_cache_creation_tokens": 0, "total_cache_read_tokens": 0,
                "avg_input_tokens_per_session": 0, "cache_hit_pct": 0.0,
                "top_tools": [],
            }

        sid_list = [s["id"] for s in sessions]
        placeholders = ",".join("?" * len(sid_list))

        rows = conn.execute(
            f"SELECT metadata FROM messages WHERE session_id IN ({placeholders})",
            sid_list,
        ).fetchall()

        tool_rows = conn.execute(
            f"""
            SELECT tool_name, COUNT(*) AS cnt
            FROM tool_calls
            WHERE message_id IN (
                SELECT id FROM messages WHERE session_id IN ({placeholders})
            )
            GROUP BY tool_name ORDER BY cnt DESC LIMIT 10
            """,
            sid_list,
        ).fetchall()

    input_t = output_t = cache_c = cache_r = 0
    for r in rows:
        meta = json.loads(r["metadata"]) if r["metadata"] else {}
        input_t  += meta.get("input_tokens", 0)
        output_t += meta.get("output_tokens", 0)
        cache_c  += meta.get("cache_creation_tokens", 0)
        cache_r  += meta.get("cache_read_tokens", 0)

    n = len(sid_list)
    total_prompt = input_t + cache_c + cache_r
    return {
        "agent_id": agent_id,
        "days": days,
        "session_count": n,
        "total_input_tokens": input_t,
        "total_output_tokens": output_t,
        "total_cache_creation_tokens": cache_c,
        "total_cache_read_tokens": cache_r,
        "avg_input_tokens_per_session": round(input_t / n) if n else 0,
        "cache_hit_pct": round(cache_r / total_prompt * 100, 1) if total_prompt else 0.0,
        "top_tools": [{"tool": r["tool_name"], "count": r["cnt"]} for r in tool_rows],
    }
