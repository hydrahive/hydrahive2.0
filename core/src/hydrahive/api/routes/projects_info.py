"""Project info routes (sessions list, stats, agent)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.projects import config as project_config

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/{project_id}/sessions")
def list_project_sessions(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)
    username, role = auth
    all_sessions = sessions_db.list_for_user(username) if role != "admin" else \
        sessions_db.list_for_agent(p["agent_id"])
    return [
        {"id": s.id, "agent_id": s.agent_id, "user_id": s.user_id,
         "project_id": s.project_id, "title": s.title, "status": s.status,
         "created_at": s.created_at, "updated_at": s.updated_at}
        for s in all_sessions if s.project_id == project_id
    ]


@router.get("/{project_id}/stats")
def get_project_stats(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)
    agent_id = p.get("agent_id", "")
    all_sessions = sessions_db.list_for_agent(agent_id, limit=500)
    project_sessions = [s for s in all_sessions if s.project_id == project_id]
    active = sum(1 for s in project_sessions if s.status == "active")
    last_activity = max((s.updated_at for s in project_sessions), default=None)
    with db() as conn:
        session_ids = [s.id for s in project_sessions]
        msg_count = token_total = 0
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            row = conn.execute(
                f"SELECT COUNT(*) as cnt, COALESCE(SUM(token_count),0) as tok "
                f"FROM messages WHERE session_id IN ({placeholders}) AND role='assistant'",
                session_ids,
            ).fetchone()
            if row:
                msg_count, token_total = row["cnt"], row["tok"]
    return {
        "total_sessions": len(project_sessions),
        "active_sessions": active,
        "total_messages": msg_count,
        "total_tokens": token_total,
        "last_activity": last_activity,
    }


@router.get("/{project_id}/agent")
def get_project_agent(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(p, *auth)
    agent = agent_config.get(p.get("agent_id", ""))
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "project_agent_not_found")
    return agent
