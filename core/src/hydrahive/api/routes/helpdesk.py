"""Hilfe-Assistent: Zustand und Senden für das Fenster unten rechts (docs/plans/help-assistant.md).

- GET  /api/helpdesk/state    – eigener Hilfe-Agent + Sitzung; ohne Standard-Modell model_missing=True
- POST /api/helpdesk/messages – Nachricht in die EIGENE Hilfe-Sitzung, mit der aktuellen Seite als System-Kontext
  (extra_system, nicht im User-Text – dort könnte ihn der Nutzer nicht sehen und das Modell ihn nicht von
  Nutzer-Text unterscheiden). Antwort ist derselbe SSE-Stream wie im normalen Chat.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._session_msg_helpers import SessionAlreadyRunning, run_and_stream
from hydrahive.helpdesk._agent import get_or_create_help_agent
from hydrahive.helpdesk._context import context_block

router = APIRouter(prefix="/api/helpdesk", tags=["helpdesk"])
_Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/state")
def helpdesk_state(auth: _Auth) -> dict:
    return get_or_create_help_agent(auth[0])


class HelpMessage(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=4000)
    path: str = Field(default="", max_length=400)


@router.post("/messages")
async def helpdesk_message(body: HelpMessage, auth: _Auth):
    state = get_or_create_help_agent(auth[0])
    if state["model_missing"]:
        raise coded(status.HTTP_409_CONFLICT, "helpdesk_model_missing")
    if body.session_id != state["session_id"]:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    from hydrahive.runner._language_rule import language_for
    try:
        return await run_and_stream(state["session_id"], body.text,
                                    extra_system=context_block(body.path, language_for(auth[0])))
    except SessionAlreadyRunning:
        raise coded(status.HTTP_409_CONFLICT, "session_already_running")
