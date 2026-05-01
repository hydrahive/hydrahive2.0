from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.db.connection import db
from hydrahive.projects import ProjectValidationError, config as project_config
from hydrahive.projects import members as project_members
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    members: list[str] = []
    llm_model: str
    init_git: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    members: list[str] | None = None


def _check_access(project: dict, username: str, role: str) -> None:
    if role == "admin":
        return
    if username in project.get("members", []) or project.get("created_by") == username:
        return
    raise coded(status.HTTP_403_FORBIDDEN, "project_no_access")


@router.get("")
def list_projects(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, role = auth
    if role == "admin":
        return project_config.list_all()
    return project_config.list_for_user(username)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    auth: Annotated[tuple[str, str], Depends(require_admin)],
) -> dict:
    creator, _ = auth
    try:
        return project_config.create(
            name=req.name,
            description=req.description,
            members=req.members,
            llm_model=req.llm_model,
            created_by=creator,
            init_git=req.init_git,
        )
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.get("/{project_id}")
def get_project(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    _check_access(p, *auth)
    return p


@router.patch("/{project_id}", dependencies=[Depends(require_admin)])
def update_project(project_id: str, req: ProjectUpdate) -> dict:
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return project_config.update(project_id, **changes)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_project(project_id: str) -> None:
    if not project_config.delete(project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")



@router.post("/{project_id}/members/{username}", dependencies=[Depends(require_admin)])
def add_member(project_id: str, username: str) -> dict:
    try:
        return project_members.add(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    except ProjectValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(e))


@router.delete("/{project_id}/members/{username}", dependencies=[Depends(require_admin)])
def remove_member(project_id: str, username: str) -> dict:
    try:
        return project_members.remove(project_id, username)
    except KeyError:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


@router.get("/{project_id}/sessions")
def list_project_sessions(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    _check_access(p, *auth)
    username, role = auth
    out = []
    all_sessions = sessions_db.list_for_user(username) if role != "admin" else \
        sessions_db.list_for_agent(p["agent_id"])
    for s in all_sessions:
        if s.project_id == project_id:
            out.append({
                "id": s.id, "agent_id": s.agent_id, "user_id": s.user_id,
                "project_id": s.project_id, "title": s.title, "status": s.status,
                "created_at": s.created_at, "updated_at": s.updated_at,
            })
    return out


@router.get("/{project_id}/stats")
def get_project_stats(
    project_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    p = project_config.get(project_id)
    if not p:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    _check_access(p, *auth)
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
    _check_access(p, *auth)
    agent = agent_config.get(p.get("agent_id", ""))
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "project_agent_not_found")
    return agent
