from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._sessions_helpers import (
    SessionCreate,
    SessionUpdate,
    check_owner,
    serialize_session,
)
from hydrahive.api.routes.sessions_messages import messages_router
from hydrahive.db import sessions as sessions_db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
router.include_router(messages_router)


@router.get("")
def list_sessions(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, _ = auth
    return [serialize_session(s) for s in sessions_db.list_for_user(username)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    req: SessionCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    agent = agent_config.get(req.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    s = sessions_db.create(
        agent_id=req.agent_id,
        user_id=username,
        project_id=req.project_id,
        title=req.title or f"Chat mit {agent['name']}",
    )
    return serialize_session(s)


@router.get("/{session_id}")
def get_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    return serialize_session(s)


@router.patch("/{session_id}")
def update_session(
    session_id: str,
    req: SessionUpdate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    sessions_db.update(session_id, title=req.title, status=req.status)
    return serialize_session(sessions_db.get(session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    sessions_db.delete(session_id)
