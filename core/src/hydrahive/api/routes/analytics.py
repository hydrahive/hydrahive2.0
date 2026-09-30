"""Analytics — Token-Audit-Dashboard (Issue #130).

Liefert pro-User (oder admin-weit) Token-/Cost-Stats für das Dashboard.
Übersicht (today, last_7d, Top-5) aus den Ereignistabellen nach Ereigniszeit
(db/usage_window.py, Task a1b95d3b); Session-Detail aus der session_metrics-VIEW.
Reiner Read-Aggregator, kein eigener Schreib-Path.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._dashboard_helpers import today_start_iso, week_start_iso
from hydrahive.db import usage_window
from hydrahive.db.connection import db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def overview(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Top-Level-Stats fürs Dashboard.

    Returns:
        today: heute-Aggregat (deutscher Kalendertag, nach Ereigniszeit)
        last_7d: 7-Tage-Aggregat (7 deutsche Kalendertage, nach Ereigniszeit)
        top_cost_sessions: 5 teuerste Sessions nach Kosten IM 7-Tage-Fenster
        by_model: aufschlüsselung pro Modell (last 7d), inkl. gemessener
                  Geschwindigkeit (tok_per_s) und mittlerer Call-Dauer (avg_ms).
                  Beide nur über Calls mit total_ms > 0 und completion_tokens > 0
                  gemittelt — Calls ohne Timing/Output verzerren sonst den Wert.
                  NULL wenn ein Modell keine auswertbaren Calls hat.
    """
    username, role = auth
    # Nach Ereigniszeit und deutschem Kalendertag (Task a1b95d3b). Vorher
    # zählte die View session_metrics nur Sessions, die im Zeitraum begonnen
    # hatten; Aktivität in älteren Sessions fehlte komplett.
    today = today_start_iso()
    seven_days = week_start_iso()
    who = None if role == "admin" else username

    with db() as conn:
        today_row = usage_window.totals(conn, since=today, username=who)
        row_7d = usage_window.totals(conn, since=seven_days, username=who)
        top_rows = usage_window.top_sessions(conn, since=seven_days, username=who, limit=5)

        # Pro-Modell-Aufschlüsselung (last 7d) — direkt aus llm_calls
        if role == "admin":
            by_model_rows = conn.execute(
                """SELECT model,
                          COUNT(*) AS calls,
                          SUM(prompt_tokens) AS input_tokens,
                          SUM(completion_tokens) AS output_tokens,
                          SUM(cache_read_tokens) AS cache_read_tokens,
                          SUM(cost_micros) AS cost_micros,
                          AVG(CASE WHEN total_ms > 0 AND completion_tokens > 0
                                   THEN completion_tokens * 1000.0 / total_ms END) AS tok_per_s,
                          AVG(CASE WHEN total_ms > 0 AND completion_tokens > 0
                                   THEN total_ms END) AS avg_ms
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
                          SUM(lc.cost_micros) AS cost_micros,
                          AVG(CASE WHEN lc.total_ms > 0 AND lc.completion_tokens > 0
                                   THEN lc.completion_tokens * 1000.0 / lc.total_ms END) AS tok_per_s,
                          AVG(CASE WHEN lc.total_ms > 0 AND lc.completion_tokens > 0
                                   THEN lc.total_ms END) AS avg_ms
                   FROM llm_calls lc
                   WHERE lc.created_at >= ?
                     AND lc.user_id = ?
                   GROUP BY lc.model
                   ORDER BY cost_micros DESC""",
                (seven_days, username),
            ).fetchall()

    return {
        "today": today_row,
        "last_7d": row_7d,
        "top_cost_sessions": top_rows,
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
