"""Bindeglied zwischen eingehenden Channel-Events und dem Agent-Runner.

Channels rufen `run_master_for_event(event)` auf — sucht den Master-Agent
des Ziel-Users, findet/erzeugt die Session pro (Channel, Sender), startet
den Runner, sammelt die finale Assistant-Antwort als String.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config
from hydrahive.communication import _session_lookup
from hydrahive.communication.base import IncomingEvent
from hydrahive.runner import run as runner_run
from hydrahive.runner.events import Done, Error, MessageStart, TextBlock, TextDelta

logger = logging.getLogger(__name__)


class NoMasterError(RuntimeError):
    """User hat keinen Master-Agent (z.B. LLM noch nicht konfiguriert)."""


def _find_master(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("type") == "master" and a.get("status") != "disabled":
            return a
    return None


async def run_master_for_event(event: IncomingEvent) -> str:
    """Verarbeitet ein eingehendes Channel-Event durch den Master-Agent."""
    master = _find_master(event.target_username)
    if not master:
        raise NoMasterError(f"kein Master-Agent für '{event.target_username}'")
    return await _run_agent(master["id"], event, prefix=None)


async def run_agent_for_event(
    agent_id: str, event: IncomingEvent, *, prefix: str | None = None,
) -> str:
    """Wie run_master_for_event, aber mit explizitem Agent (z.B. aus
    Butler `agent_reply`/`agent_reply_with_prefix`)."""
    return await _run_agent(agent_id, event, prefix=prefix)


async def _run_agent(agent_id: str, event: IncomingEvent, *, prefix: str | None) -> str:
    session = _session_lookup.find_or_create(
        agent_id=agent_id,
        user_id=event.target_username,
        channel=event.channel,
        external_user_id=event.external_user_id,
        title_hint=f"{event.channel}: {event.sender_name or event.external_user_id}",
    )
    user_text = event.text
    if prefix:
        user_text = f"[BUTLER-VORGABE: {prefix}]\n\n{event.text}"

    answer_parts: list[str] = []
    current_text: list[str] = []
    async for ev in runner_run(session.id, user_text):
        if isinstance(ev, MessageStart):
            current_text = []
        elif isinstance(ev, TextDelta):
            current_text.append(ev.text)
        elif isinstance(ev, TextBlock):
            if current_text:
                answer_parts.append("".join(current_text))
                current_text = []
        elif isinstance(ev, Done):
            if current_text:
                answer_parts.append("".join(current_text))
            break
        elif isinstance(ev, Error):
            logger.error("Runner-Fehler im Channel-Run: %s", ev.message)
            raise RuntimeError(ev.message)

    return "\n\n".join(p for p in answer_parts if p.strip())
