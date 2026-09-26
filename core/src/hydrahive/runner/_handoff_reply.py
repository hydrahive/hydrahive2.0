"""Build and deliver bounded AgentLink handoff reply states."""
from __future__ import annotations

import logging

from hydrahive.agentlink.client import post_state
from hydrahive.agentlink.protocol import (
    ContextBlock,
    Handoff,
    State,
    TaskBlock,
    WorkingMemory,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
_MAX_REPLY_CHARS = 12_000


def bounded_reply(output: str) -> str:
    if len(output) <= _MAX_REPLY_CHARS:
        return output
    marker = "\n...[Antwort gekürzt]...\n"
    head = _MAX_REPLY_CHARS * 3 // 4
    tail = _MAX_REPLY_CHARS - head - len(marker)
    return output[:head] + marker + output[-tail:]


async def post_reply(
    incoming: State, output: str, status: str, *, checkpoint: str | None = None,
) -> bool:
    desc = incoming.task.description if incoming.task else ""
    protocol_status = "done" if status == "done" else "blocked"
    findings = [bounded_reply(output), *([checkpoint] if checkpoint else [])]
    reply = State(
        agent_id=settings.agentlink_agent_id,
        task=TaskBlock(
            type=incoming.task.type if incoming.task else "feature",
            description=(
                f"Abgeschlossen: {desc[:100]}" if status == "done"
                else f"Pausiert: {output[-100:]}" if status == "paused"
                else f"Fehler: {output[-100:]}"
            ),
            status=protocol_status,
        ),
        context=ContextBlock(),
        working_memory=WorkingMemory(findings=findings),
        handoff=Handoff(
            to_agent=settings.agentlink_agent_id,
            reason=f"reply_to:{incoming.id}",
        ),
    )
    try:
        await post_state(reply)
        logger.info("handoff_receiver: Antwort-State gepostet (reply_to:%s)", incoming.id)
        return True
    except Exception as exc:
        logger.error("handoff_receiver: Antwort-State posten fehlgeschlagen: %s", exc)
        return False


async def post_error_reply(incoming: State, message: str) -> None:
    await post_reply(incoming, message, "error")
