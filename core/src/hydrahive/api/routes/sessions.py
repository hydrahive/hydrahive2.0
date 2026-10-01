from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config
from hydrahive.api.routes._sessions_helpers import (
    SessionCreate,
    SessionUpdate,
    check_owner,
    serialize_session,
)
from hydrahive.api.routes.sessions_delegations import delegations_router
from hydrahive.api.routes.sessions_messages import messages_router
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import tool_confirmation
from pydantic import BaseModel


class ToolConfirmDecision(BaseModel):
    decision: str  # "approve" | "deny"

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
router.include_router(messages_router)
router.include_router(delegations_router)


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
    project = None
    if req.project_id:
        # Wie PATCH: das Projekt bestimmt Workspace, Skills und Tools des Runs.
        project = _assert_project_access(req.project_id, *auth)
    _assert_agent_access(agent, project, *auth)
    s = sessions_db.create(
        agent_id=req.agent_id,
        user_id=username,
        project_id=req.project_id,
        title=req.title or f"Chat mit {agent['name']}",
    )
    return serialize_session(s)


@router.post("/{session_id}/handover")
async def create_handover(
    session_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    if not s.project_id:
        return {"written": False, "reason": "session_without_project"}
    agent = agent_config.get(s.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    from hydrahive.handover import create_for_session
    path = await create_for_session(
        session_id,
        model=agent.get("compact_model") or agent["llm_model"],
        tool_result_limit=agent.get("compact_tool_result_limit"),
    )
    return {"written": path is not None}


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
    # model_override getrennt — unter metadata, read-modify-write
    if req.model_override is not None:
        sessions_db.set_model_override(session_id, req.model_override or None)
    # reasoning_effort getrennt — unter metadata, read-modify-write
    if req.reasoning_effort is not None:
        sessions_db.set_reasoning_effort(session_id, req.reasoning_effort or None)
    # buddy_mode — Stil-Hinweis nur für den Buddy, unter metadata
    if req.buddy_mode is not None:
        sessions_db.set_buddy_mode(session_id, req.buddy_mode or None)
    # project_id getrennt — eigene Spalte; bestimmt das Run-Arbeitsverzeichnis.
    if req.project_id is not None:
        pid = req.project_id or None
        if pid is not None:
            _assert_project_access(pid, *auth)
        sessions_db.set_project(session_id, pid)
    return serialize_session(sessions_db.get(session_id))


def _assert_project_access(project_id: str, username: str, role: str) -> dict:
    """Eine Session an ein Projekt heften ist schreibend -> Rolle write nötig."""
    proj = project_config.get(project_id)
    if not proj:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(proj, username, role, required="write")
    return proj


def _assert_agent_access(agent: dict, project: dict | None, username: str, role: str) -> None:
    """Nur eigene Agenten, oder Agenten des Projekts, an das die Session hängt.

    Vorher wurde nur geprüft, ob der Agent existiert. Damit konnte jeder
    Login eine Session mit einem fremden Buddy anlegen und darüber mit ihm
    arbeiten, weil check_owner später nur den Session-Besitzer prüft.
    Projekt-Mitglieder (write) dürfen weiter den Projekt-Agenten und die
    freigegebenen Spezialisten des Projekts nutzen, aber nur mit project_id:
    Ohne sie hätte die Session den Agenten, aber weder Workspace noch Skills
    des Projekts.
    """
    if role == "admin" or agent.get("owner") == username:
        return
    if project is not None:
        team = {project.get("agent_id"), *(project.get("allowed_specialists") or [])}
        if agent["id"] in team:
            return
    raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")


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


@router.post("/{session_id}/tool-confirm/{call_id}")
def tool_confirm(
    session_id: str,
    call_id: str,
    body: ToolConfirmDecision,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    if body.decision not in ("approve", "deny"):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_decision")
    ok = tool_confirmation.resolve(call_id, body.decision)  # type: ignore[arg-type]
    if not ok:
        raise coded(status.HTTP_404_NOT_FOUND, "no_pending_confirmation")
    return {"resolved": True, "decision": body.decision}
