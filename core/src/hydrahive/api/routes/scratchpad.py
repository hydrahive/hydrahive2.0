"""Scratchpad-Endpoints: Mensch-Zone editierbar, Agent-Zone read-only + leerbar."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge

router = APIRouter(prefix="/api/scratchpad", tags=["scratchpad"])


class ScratchpadBody(BaseModel):
    content: str = Field(default="", max_length=262144)


@router.get("")
def get_scratchpad(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    return {"user_content": service.get_user(user), "agent_content": service.get_agent(user)}


@router.put("")
def put_scratchpad(
    body: ScratchpadBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    try:
        service.save_user(user, body.content)
    except ScratchpadTooLarge as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "scratchpad_too_large", message=str(e))
    return {"saved": True}


@router.delete("/agent")
def clear_agent_zone(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    service.clear_agent(user)
    return {"cleared": True}
