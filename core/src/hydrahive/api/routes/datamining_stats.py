"""Token-Statistik-Endpoints für Datamining.

GET /api/datamining/stats/session/{session_id}  — Stats für eine Session
GET /api/datamining/stats/agent/{agent_id}       — Aggregat für einen Agenten
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._datamining_access import owns, scoped_username
from hydrahive.db import token_stats

router = APIRouter(prefix="/api/datamining/stats", tags=["datamining"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/daily")
def get_daily_stats(
    auth: Auth,
    agent_id: str | None = None,
    days: int = 14,
) -> dict:
    rows = token_stats.daily_stats(agent_id=agent_id or None, days=min(days, 90),
                                   user_id=scoped_username(auth))
    return {"days": rows}


@router.get("/latest")
def get_latest_sessions(auth: Auth, count: int = 5) -> dict:
    sessions = token_stats.latest_sessions(count=min(count, 50), user_id=scoped_username(auth))
    return {"sessions": sessions}


@router.get("/session/{session_id}")
def get_session_stats(session_id: str, auth: Auth) -> dict:
    result = token_stats.session_stats(session_id)
    if result is None or not owns(auth, result.get("user_id")):
        raise HTTPException(404, "Session nicht gefunden")
    return result


@router.get("/agent/{agent_id}")
def get_agent_stats(agent_id: str, auth: Auth, days: int = 7) -> dict:
    return token_stats.agent_stats(agent_id, days=min(days, 90), user_id=scoped_username(auth))
