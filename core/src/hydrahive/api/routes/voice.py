"""Home Assistant Conversation Agent — POST /api/voice/chat.

HA's voice pipeline schickt Text + conversation_id, wir antworten mit einem
flachen Reply-String. Tool-Calls werden serverseitig abgearbeitet, nur
finaler Text geht raus.

Auth: API-Key (hhk_*) oder JWT. Owner-Check auf den Agent.
Siehe SPEC.md "Home Assistant — Conversation Agent".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._agent_schemas import check_agent_access
from hydrahive.db import messages as messages_db
from hydrahive.runner import run as runner_run
from hydrahive.runner.events import Done, Error
from hydrahive.voice._ha_conversation import get_or_create_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

VOICE_TIMEOUT_S = 25.0


class VoiceChatBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str = Field(..., min_length=1, max_length=200)
    agent_id: str = Field(..., min_length=1)
    language: str | None = Field(default=None, max_length=10)


class VoiceChatResponse(BaseModel):
    reply: str
    conversation_id: str
    end_conversation: bool = False


def _extract_text(blocks: list | str) -> str:
    """Extrahiert nur Text-Blocks aus einer assistant-Message — Tool-Use raus."""
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ""
    parts: list[str] = []
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text":
            t = b.get("text", "")
            if t:
                parts.append(t)
    return "\n".join(parts).strip()


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    body: VoiceChatBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> VoiceChatResponse:
    username, role = auth

    agent = agent_config.get(body.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    check_agent_access(agent, username, role)

    session_id = get_or_create_session(
        body.conversation_id,
        agent_id=body.agent_id,
        user_id=username,
    )

    extra_system = None
    if body.language:
        extra_system = f"Antworte auf Sprache: {body.language}."

    final_message_id: str | None = None
    error_msg: str | None = None

    async def _drive() -> None:
        nonlocal final_message_id, error_msg
        async for ev in runner_run(session_id, body.text, extra_system=extra_system):
            if isinstance(ev, Done):
                final_message_id = ev.message_id
                return
            if isinstance(ev, Error):
                error_msg = ev.message
                return

    try:
        await asyncio.wait_for(_drive(), timeout=VOICE_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning(
            "voice/chat: Timeout nach %ss (session=%s)", VOICE_TIMEOUT_S, session_id
        )
        raise coded(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "voice_timeout",
            message=f"Agent hat länger als {int(VOICE_TIMEOUT_S)}s gebraucht.",
        )

    if error_msg:
        raise coded(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "voice_run_failed", message=error_msg
        )
    if not final_message_id:
        raise coded(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "voice_run_failed",
            message="Runner endete ohne Done-Event",
        )

    msg = messages_db.get(final_message_id)
    if not msg:
        raise coded(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "voice_run_failed",
            message="Final-Message nicht gefunden",
        )

    reply = _extract_text(msg.content)
    if not reply:
        reply = "(Kein Text-Output vom Agent.)"

    return VoiceChatResponse(reply=reply, conversation_id=body.conversation_id)
