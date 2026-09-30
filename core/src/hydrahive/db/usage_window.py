"""Nutzung in einem Zeitfenster, gezählt nach EREIGNISZEIT (Task a1b95d3b).

Die View session_metrics grenzt über den Session-Beginn ab. Fürs Dashboard
(„heute“, „7 Tage“) ist das falsch: Alles, was heute in einer älteren Session
passiert, fehlte (30.09.2026: Kachel 0,03 $, echt 223 $). Hier wird direkt aus
den Ereignistabellen summiert, jeweils nach deren created_at.

`since` ist ein UTC-Zeitstempel im Speicherformat (…+00:00), siehe
_dashboard_helpers.today_start_iso(). `username=None` = alle (Admin).
Tool-Abstürze stehen in tool_calls UND errors_log (#484); sie zählen nur
als tool_errors, nicht zusätzlich in errors.
"""
from __future__ import annotations

from hydrahive.db.errors_log import CRASH_SOURCES


def _where(since: str, username: str | None, col: str = "created_at",
           user_col: str = "user_id") -> tuple[str, tuple]:
    if username is None:
        return f"{col} >= ?", (since,)
    return f"{col} >= ? AND {user_col} = ?", (since, username)


def totals(conn, *, since: str, username: str | None) -> dict:
    w, p = _where(since, username)
    llm = conn.execute(
        f"""SELECT COALESCE(SUM(prompt_tokens), 0)         AS input_tokens,
                   COALESCE(SUM(completion_tokens), 0)     AS output_tokens,
                   COALESCE(SUM(cache_read_tokens), 0)     AS cache_read_tokens,
                   COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens,
                   COALESCE(SUM(cost_micros), 0)           AS cost_micros,
                   COUNT(*)                                AS llm_calls,
                   COUNT(DISTINCT session_id)              AS sessions
            FROM llm_calls WHERE {w}""", p).fetchone()
    tools = conn.execute(
        f"""SELECT COUNT(*) AS tool_calls,
                   COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) AS tool_errors
            FROM tool_calls WHERE {w}""", p).fetchone()
    compactions = conn.execute(f"SELECT COUNT(*) FROM compaction_events WHERE {w}", p).fetchone()[0]
    ph = ",".join("?" * len(CRASH_SOURCES))
    errors = conn.execute(
        f"SELECT COUNT(*) FROM errors_log WHERE {w} AND source NOT IN ({ph})",
        (*p, *CRASH_SOURCES)).fetchone()[0]
    return {**dict(llm), **dict(tools), "compactions": compactions, "errors": errors}


def top_sessions(conn, *, since: str, username: str | None, limit: int = 5) -> list[dict]:
    """Teuerste Sessions nach Kosten IM Zeitfenster (nicht Gesamtkosten)."""
    w, p = _where(since, username, col="lc.created_at", user_col="lc.user_id")
    ph = ",".join("?" * len(CRASH_SOURCES))
    rows = conn.execute(
        f"""SELECT lc.session_id, s.agent_id, s.title, s.created_at,
                   SUM(lc.cost_micros)       AS cost_micros,
                   SUM(lc.prompt_tokens)     AS input_tokens,
                   SUM(lc.completion_tokens) AS output_tokens,
                   SUM(lc.cache_read_tokens) AS cache_read_tokens,
                   COUNT(*)                  AS llm_calls,
                   (SELECT COUNT(*) FROM tool_calls t
                     WHERE t.session_id = lc.session_id AND t.created_at >= ?) AS tool_calls,
                   (SELECT COUNT(*) FROM errors_log e
                     WHERE e.session_id = lc.session_id AND e.created_at >= ?
                       AND e.source NOT IN ({ph})) AS errors
            FROM llm_calls lc JOIN sessions s ON s.id = lc.session_id
            WHERE {w}
            GROUP BY lc.session_id
            HAVING SUM(lc.cost_micros) > 0
            ORDER BY cost_micros DESC
            LIMIT ?""",
        (since, since, *CRASH_SOURCES, *p, limit)).fetchall()
    return [dict(r) for r in rows]
