from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.routes._sse import to_sse
from hydrahive.compaction import compact_session, total_tokens
from hydrahive.compaction.compactor import DEFAULT_RESERVE_TOKENS
from hydrahive.compaction.tokens import context_window_for
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import run as runner_run

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    agent_id: str
    title: str | None = None
    project_id: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


class MessageCreate(BaseModel):
    text: str = Field(..., min_length=1)


def _check_owner(session, username: str, role: str) -> None:
    if role != "admin" and session.user_id != username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kein Zugriff auf diese Session")


def _serialize_session(s) -> dict:
    return {
        "id": s.id,
        "agent_id": s.agent_id,
        "user_id": s.user_id,
        "project_id": s.project_id,
        "title": s.title,
        "status": s.status,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "metadata": s.metadata,
    }


def _serialize_message(m) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at,
        "token_count": m.token_count,
        "metadata": m.metadata,
    }


@router.get("")
def list_sessions(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    username, _ = auth
    return [_serialize_session(s) for s in sessions_db.list_for_user(username)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    req: SessionCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    agent = agent_config.get(req.agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent nicht gefunden")
    s = sessions_db.create(
        agent_id=req.agent_id,
        user_id=username,
        project_id=req.project_id,
        title=req.title or f"Chat mit {agent['name']}",
    )
    return _serialize_session(s)


@router.get("/{session_id}")
def get_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    return _serialize_session(s)


@router.patch("/{session_id}")
def update_session(
    session_id: str,
    req: SessionUpdate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    sessions_db.update(session_id, title=req.title, status=req.status)
    return _serialize_session(sessions_db.get(session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> None:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    sessions_db.delete(session_id)


@router.get("/{session_id}/messages")
def list_messages(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> list[dict]:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    return [_serialize_message(m) for m in messages_db.list_for_session(session_id)]


@router.get("/{session_id}/tokens")
def get_tokens(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    agent = agent_config.get(s.agent_id)
    history = messages_db.list_for_llm(session_id) if agent else []
    used = total_tokens(history)
    window = context_window_for(agent["llm_model"]) if agent else 0
    threshold = max(0, window - DEFAULT_RESERVE_TOKENS)
    return {
        "used": used,
        "context_window": window,
        "compact_threshold": threshold,
        "model": agent["llm_model"] if agent else None,
    }


@router.post("/{session_id}/compact")
async def manual_compact(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    instructions: str | None = None,
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)
    agent = agent_config.get(s.agent_id)
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent nicht gefunden")
    try:
        return await compact_session(session_id, model=agent["llm_model"], instructions=instructions)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/{session_id}/messages")
async def post_message(
    session_id: str,
    req: MessageCreate,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> StreamingResponse:
    s = sessions_db.get(session_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session nicht gefunden")
    _check_owner(s, *auth)

    events = runner_run(session_id, req.text)
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
