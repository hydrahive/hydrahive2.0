"""Analytics — Token-Audit-Dashboard (Issue #130).

Liefert pro-User (oder admin-weit) Token-/Cost-Stats für das Dashboard.
Daten kommen aus session_metrics-VIEW (Token-Audit #129) — diese Route
ist ein Read-Aggregator, kein eigener Schreib-Path.
"""
from __future__ import annotations

import datetime as _dt
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._dashboard_helpers import today_start_iso
from hydrahive.db.connection import db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _seven_days_ago_iso() -> str:
    return (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=7)).isoformat(timespec="seconds")


@router.get("/overview")
def overview(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Top-Level-Stats fürs Dashboard.

    Returns:
        today: heute-Aggregat (tokens, cost_micros, errors)
        last_7d: 7-Tage-Aggregat
        top_cost_sessions: 5 teuerste Sessions im Zeitfenster
        by_model: aufschlüsselung pro Modell (last 7d)
    """
    username, role = auth
    today = today_start_iso()
    seven_days = _seven_days_ago_iso()

    # Qualifiziert mit Tabellen-Prefix da der TOP-Cost-Query joinst und
    # 'user_id' sowohl in session_metrics als auch in sessions vorkommt.
    where_user = "" if role == "admin" else " AND m.user_id = ?"
    where_user_unqualified = "" if role == "admin" else " AND user_id = ?"
    params_today: tuple = (today,) if role == "admin" else (today, username)
    params_7d: tuple = (seven_days,) if role == "admin" else (seven_days, username)

    with db() as conn:
        # heute
        row_today = conn.execute(
            f"""SELECT
                  COALESCE(SUM(input_tokens), 0)               AS input_tokens,
                  COALESCE(SUM(output_tokens), 0)              AS output_tokens,
                  COALESCE(SUM(cache_read_tokens), 0)          AS cache_read_tokens,
                  COALESCE(SUM(cache_creation_tokens), 0)      AS cache_creation_tokens,
                  COALESCE(SUM(cost_micros), 0)                AS cost_micros,
                  COALESCE(SUM(llm_calls), 0)                  AS llm_calls,
                  COALESCE(SUM(tool_calls), 0)                 AS tool_calls,
                  COALESCE(SUM(tool_errors), 0)                AS tool_errors,
                  COALESCE(SUM(compactions), 0)                AS compactions,
                  COALESCE(SUM(errors), 0)                     AS errors,
                  COUNT(*)                                     AS sessions
               FROM session_metrics
               WHERE created_at >= ?{where_user_unqualified}""",
            params_today,
        ).fetchone()

        # last 7d
        row_7d = conn.execute(
            f"""SELECT
                  COALESCE(SUM(input_tokens), 0)               AS input_tokens,
                  COALESCE(SUM(output_tokens), 0)              AS output_tokens,
                  COALESCE(SUM(cache_read_tokens), 0)          AS cache_read_tokens,
                  COALESCE(SUM(cache_creation_tokens), 0)      AS cache_creation_tokens,
                  COALESCE(SUM(cost_micros), 0)                AS cost_micros,
                  COALESCE(SUM(llm_calls), 0)                  AS llm_calls,
                  COALESCE(SUM(errors), 0)                     AS errors,
                  COUNT(*)                                     AS sessions
               FROM session_metrics
               WHERE created_at >= ?{where_user_unqualified}""",
            params_7d,
        ).fetchone()

        # Top-5 teuerste Sessions (last 7d)
        top_rows = conn.execute(
            f"""SELECT m.session_id, m.agent_id, m.cost_micros,
                       m.input_tokens, m.output_tokens, m.cache_read_tokens,
                       m.llm_calls, m.tool_calls, m.errors,
                       s.title, s.created_at
               FROM session_metrics m
               JOIN sessions s ON s.id = m.session_id
               WHERE m.created_at >= ?{where_user} AND m.cost_micros > 0
               ORDER BY m.cost_micros DESC
               LIMIT 5""",
            params_7d,
        ).fetchall()

        # Pro-Modell-Aufschlüsselung (last 7d) — direkt aus llm_calls
        if role == "admin":
            by_model_rows = conn.execute(
                """SELECT model,
                          COUNT(*) AS calls,
                          SUM(prompt_tokens) AS input_tokens,
                          SUM(completion_tokens) AS output_tokens,
                          SUM(cache_read_tokens) AS cache_read_tokens,
                          SUM(cost_micros) AS cost_micros
                   FROM llm_calls
                   WHERE created_at >= ?
                   GROUP BY model
                   ORDER BY cost_micros DESC""",
                (seven_days,),
            ).fetchall()
        else:
            by_model_rows = conn.execute(
                """SELECT lc.model,
                          COUNT(*) AS calls,
                          SUM(lc.prompt_tokens) AS input_tokens,
                          SUM(lc.completion_tokens) AS output_tokens,
                          SUM(lc.cache_read_tokens) AS cache_read_tokens,
                          SUM(lc.cost_micros) AS cost_micros
                   FROM llm_calls lc
                   WHERE lc.created_at >= ?
                     AND lc.user_id = ?
                   GROUP BY lc.model
                   ORDER BY cost_micros DESC""",
                (seven_days, username),
            ).fetchall()

    return {
        "today": dict(row_today) if row_today else {},
        "last_7d": dict(row_7d) if row_7d else {},
        "top_cost_sessions": [dict(r) for r in top_rows],
        "by_model": [dict(r) for r in by_model_rows],
    }


@router.get("/session/{session_id}")
def session_detail(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Telemetrie-Detail einer Session — alle Aggregate + Listen der Events."""
    from dataclasses import asdict
    from hydrahive.db import errors_log
    from hydrahive.db import llm_calls as llm_calls_db
    from hydrahive.db import compaction_events as compaction_events_db
    from hydrahive.db import session_metrics
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db
    from hydrahive.agents import config as agent_config

    username, role = auth
    s = sessions_db.get(session_id)
    if not s:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="session_not_found")
    if role != "admin" and s.user_id != username:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="forbidden")

    metrics = session_metrics.for_session(session_id)
    agent = agent_config.get(s.agent_id) if s.agent_id else None

    tool_calls_raw = tools_db.list_for_session(session_id)
    tool_calls = []
    for tc in tool_calls_raw:
        d = asdict(tc)
        # arguments + result sind potenziell groß — kürzen damit Response klein bleibt
        if d.get("arguments"):
            arg_str = str(d["arguments"])
            d["arguments_preview"] = arg_str[:500] + ("…" if len(arg_str) > 500 else "")
            d.pop("arguments", None)
        if d.get("result"):
            res_str = str(d["result"])
            d["result_preview"] = res_str[:500] + ("…" if len(res_str) > 500 else "")
            d.pop("result", None)
        tool_calls.append(d)

    return {
        "session": {
            "id": s.id,
            "title": s.title,
            "agent_id": s.agent_id,
            "agent_name": agent["name"] if agent else None,
            "user_id": s.user_id,
            "project_id": s.project_id,
            "status": s.status,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        },
        "metrics": metrics,
        "llm_calls": llm_calls_db.for_session(session_id),
        "tool_calls": tool_calls,
        "compactions": compaction_events_db.for_session(session_id),
        "errors": errors_log.for_session(session_id),
    }
