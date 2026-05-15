"""Aggregierte Token-Auswertungen: Zeitreihen und Agent-Übersichten."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db.connection import db


def daily_stats(agent_id: str | None = None, days: int = 14) -> list[dict[str, Any]]:
    """Token-Zeitreihe: pro Tag aggregierte Werte für Vorher/Nachher-Vergleich.

    Gibt eine Liste von Tages-Einträgen zurück (älteste zuerst), je mit:
    sessions, input_tokens, output_tokens, cache_read_tokens, cache_hit_pct.
    """
    with db() as conn:
        if agent_id:
            session_rows = conn.execute(
                """
                SELECT id, date(updated_at) AS day
                FROM sessions
                WHERE agent_id = ?
                  AND updated_at >= datetime('now', ?)
                """,
                (agent_id, f"-{days} days"),
            ).fetchall()
        else:
            session_rows = conn.execute(
                """
                SELECT id, date(updated_at) AS day
                FROM sessions
                WHERE updated_at >= datetime('now', ?)
                """,
                (f"-{days} days",),
            ).fetchall()

        if not session_rows:
            return []

        by_day: dict[str, list[str]] = {}
        for r in session_rows:
            by_day.setdefault(r["day"], []).append(r["id"])

        result = []
        for day in sorted(by_day):
            sids = by_day[day]
            placeholders = ",".join("?" * len(sids))
            meta_rows = conn.execute(
                f"SELECT metadata FROM messages WHERE session_id IN ({placeholders})",
                sids,
            ).fetchall()

            input_t = output_t = cache_c = cache_r = 0
            for mr in meta_rows:
                meta = json.loads(mr["metadata"]) if mr["metadata"] else {}
                input_t  += meta.get("input_tokens", 0)
                output_t += meta.get("output_tokens", 0)
                cache_c  += meta.get("cache_creation_tokens", 0)
                cache_r  += meta.get("cache_read_tokens", 0)

            total_prompt = input_t + cache_c + cache_r
            result.append({
                "date": day,
                "session_count": len(sids),
                "input_tokens": input_t,
                "output_tokens": output_t,
                "cache_creation_tokens": cache_c,
                "cache_read_tokens": cache_r,
                "cache_hit_pct": round(cache_r / total_prompt * 100, 1) if total_prompt else 0.0,
            })
    return result


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
