"""session_metrics: Read-Wrapper über die session_metrics-VIEW (Token-Audit #129).

Liefert pro-Session und pro-Agent aggregierte Token-/Cost-/Tool-/Compaction-
/Error-Metriken. Quelle ist die SQLite-VIEW `session_metrics` (Migration 014).
"""
from __future__ import annotations

from hydrahive.db.connection import db


def for_session(session_id: str) -> dict | None:
    """Aggregat-Zeile einer Session — None wenn Session nicht existiert."""
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM session_metrics WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def for_agent(agent_id: str, *, limit: int = 50) -> list[dict]:
    """Aktuellste N Sessions eines Agents — neueste zuerst."""
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM session_metrics
               WHERE agent_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (agent_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def for_user(user_id: str, *, limit: int = 50) -> list[dict]:
    """Aktuellste N Sessions eines Users — neueste zuerst."""
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM session_metrics
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def top_cost(
    *,
    limit: int = 20,
    since: str | None = None,
    agent_id: str | None = None,
) -> list[dict]:
    """Teuerste Sessions absteigend. `since` als ISO-Timestamp + Agent-Filter."""
    sql = "SELECT * FROM session_metrics WHERE cost_micros > 0"
    params: tuple = ()
    if since:
        sql += " AND created_at >= ?"
        params = (since,)
    if agent_id:
        sql += " AND agent_id = ?"
        params = params + (agent_id,)
    sql += " ORDER BY cost_micros DESC LIMIT ?"
    params = params + (limit,)
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def daily_rollup(*, since: str | None = None) -> list[dict]:
    """Aggregat pro Tag (UTC) — für Dashboard-Zeitreihen.

    Returnt: [{day, sessions, llm_calls, input_tokens, output_tokens,
               cache_read_tokens, cost_micros, errors}].
    """
    sql = """
        SELECT
            substr(created_at, 1, 10)            AS day,
            COUNT(*)                             AS sessions,
            SUM(llm_calls)                       AS llm_calls,
            SUM(input_tokens)                    AS input_tokens,
            SUM(output_tokens)                   AS output_tokens,
            SUM(cache_read_tokens)               AS cache_read_tokens,
            SUM(cache_creation_tokens)           AS cache_creation_tokens,
            SUM(cost_micros)                     AS cost_micros,
            SUM(tool_calls)                      AS tool_calls,
            SUM(tool_errors)                     AS tool_errors,
            SUM(compactions)                     AS compactions,
            SUM(errors)                          AS errors
        FROM session_metrics
    """
    params: tuple = ()
    if since:
        sql += " WHERE created_at >= ?"
        params = (since,)
    sql += " GROUP BY day ORDER BY day ASC"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def totals_for_agent(agent_id: str) -> dict:
    """All-time Aggregat über alle Sessions eines Agents."""
    with db() as conn:
        row = conn.execute(
            """SELECT
                   COUNT(*)                       AS sessions,
                   SUM(llm_calls)                 AS llm_calls,
                   SUM(input_tokens)              AS input_tokens,
                   SUM(output_tokens)             AS output_tokens,
                   SUM(cache_read_tokens)         AS cache_read_tokens,
                   SUM(cache_creation_tokens)     AS cache_creation_tokens,
                   SUM(cost_micros)               AS cost_micros,
                   SUM(tool_calls)                AS tool_calls,
                   SUM(tool_errors)               AS tool_errors,
                   SUM(compactions)               AS compactions,
                   SUM(errors)                    AS errors
               FROM session_metrics
               WHERE agent_id = ?""",
            (agent_id,),
        ).fetchone()
    return dict(row) if row else {}
