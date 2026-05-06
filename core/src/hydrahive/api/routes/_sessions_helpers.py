from __future__ import annotations

from fastapi import status
from pydantic import BaseModel

from hydrahive.api.middleware.errors import coded


class SessionCreate(BaseModel):
    agent_id: str
    title: str | None = None
    project_id: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    # Pro-Session-Modell-Override (Chat-Header-Switcher). Leer-String oder None
    # entfernt den Override → fallback auf Agent-Default.
    model_override: str | None = None
    # Pro-Session Reasoning-Effort-Override für Anthropic Extended Thinking.
    # "low" | "medium" | "high" | None (= aus)
    reasoning_effort: str | None = None


def check_owner(session, username: str, role: str) -> None:
    if role != "admin" and session.user_id != username:
        raise coded(status.HTTP_403_FORBIDDEN, "session_no_access")


def serialize_session(s) -> dict:
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


def attach_duration(block, tool_durations: dict[str, int]) -> dict:
    """Hängt duration_ms an tool_use- und tool_result-Blocks. Bleibt für die
    Anthropic-API-Sicht unauffällig — wird nur im Read-Path eingespielt."""
    if not isinstance(block, dict):
        return block
    btype = block.get("type")
    if btype == "tool_use":
        d = tool_durations.get(block.get("id", ""))
        if d is not None:
            return {**block, "duration_ms": d}
    elif btype == "tool_result":
        d = tool_durations.get(block.get("tool_use_id", ""))
        if d is not None:
            return {**block, "duration_ms": d}
    return block


def serialize_message(m, tool_durations: dict[str, int] | None = None) -> dict:
    """tool_durations: {tool_use_id → duration_ms} damit Frontend die Tool-Dauer
    pro tool_use bzw. tool_result-Block anzeigen kann."""
    content = m.content
    if tool_durations and isinstance(content, list):
        content = [attach_duration(b, tool_durations) for b in content]
    return {
        "id": m.id,
        "role": m.role,
        "content": content,
        "created_at": m.created_at,
        "token_count": m.token_count,
        "metadata": m.metadata,
    }
