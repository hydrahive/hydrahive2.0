"""Empfänger für eingehende AgentLink-Handoffs.

Wenn ein anderer Agent einen Task via AgentLink an uns schickt, muss HH2:
  1. Den eingehenden State laden
  2. Den Admin-Master-Agent als Empfänger bestimmen
  3. Eine neue Session erstellen
  4. Den Runner als Background-Task starten
  5. Output akkumulieren und als Antwort-State zurückposten

Dieser Flow ist die Gegenseite von tools/ask_agent.py.
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.agentlink.client import get_state, post_state
from hydrahive.agentlink.protocol import ContextBlock, Handoff, State, TaskBlock, WorkingMemory, WSEvent
from hydrahive.db import agent_handoffs as db_agent_handoffs
from hydrahive.db import sessions as sessions_db
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


async def handle(event: WSEvent) -> None:
    """Entry-Point: wird von lifespan._on_event für neue eingehende Handoffs aufgerufen."""
    if not event.state_id:
        return
    try:
        state = await get_state(event.state_id)
    except Exception as e:
        logger.warning("handoff_receiver: get_state(%s) fehlgeschlagen: %s", event.state_id, e)
        return
    if not state or not state.task:
        return

    master = _find_admin_master()
    if not master:
        logger.error("handoff_receiver: kein Master-Agent für 'admin' — Handoff abgelehnt")
        await _post_error_reply(state, "Kein Master-Agent konfiguriert")
        return

    session = sessions_db.create(
        agent_id=master["id"],
        user_id="admin",
        title=(state.task.description or "AgentLink-Task")[:80],
        metadata={"source": "agentlink", "incoming_state_id": state.id},
    )

    handoff_record = db_agent_handoffs.create(
        incoming_state_id=state.id or "",
        from_agent=state.agent_id,
        agent_id=master["id"],
        session_id=session.id,
    )

    asyncio.create_task(
        _run_and_reply(state, session.id, handoff_record["id"]),
        name=f"handoff-{state.id}",
    )
    logger.info(
        "handoff_receiver: eingehender Task von '%s' → Session %s gestartet",
        state.agent_id, session.id,
    )


def _find_admin_master() -> dict | None:
    from hydrahive.agents import config as agent_config
    agents = agent_config.list_by_owner("admin")
    return next((a for a in agents if a.get("type") == "master" and a.get("status") == "active"), None)


def _build_user_input(state: State) -> str:
    parts = [f"# Aufgabe: {state.task.description}"]
    parts.append(f"Typ: {state.task.type} | Priorität: {state.task.priority}")
    if state.context and state.context.files:
        paths = ", ".join(f.get("path", "") for f in state.context.files if f.get("path"))
        if paths:
            parts.append(f"\nDateien: {paths}")
    if state.context and state.context.errors:
        parts.append("\nFehler:\n" + "\n".join(state.context.errors))
    if state.context and state.context.git:
        parts.append(f"\nGit: {state.context.git}")
    if state.agent_id:
        parts.append(f"\n(Auftraggeber: {state.agent_id})")
    return "\n".join(parts)


async def _run_and_reply(state: State, session_id: str, handoff_db_id: str) -> None:
    from hydrahive.runner import runner
    from hydrahive.runner.events import Error

    user_input = _build_user_input(state)
    output_parts: list[str] = []
    error_msg: str | None = None

    try:
        async for ev in runner.run(session_id, user_input):
            if hasattr(ev, "text"):
                output_parts.append(ev.text)
            elif isinstance(ev, Error):
                error_msg = ev.message
                break
    except Exception as e:
        error_msg = str(e)
        logger.exception("handoff_receiver: Runner-Fehler für Session %s", session_id)

    output = "".join(output_parts) if output_parts else (error_msg or "Kein Output")
    status = "error" if error_msg else "done"

    await _post_reply(state, output, status)
    db_agent_handoffs.update_status(handoff_db_id, status)


async def _post_reply(incoming: State, output: str, status: str) -> None:
    desc = incoming.task.description if incoming.task else ""
    reply = State(
        agent_id=settings.agentlink_agent_id,
        task=TaskBlock(
            type=incoming.task.type if incoming.task else "feature",
            description=f"Abgeschlossen: {desc[:100]}" if status == "done" else f"Fehler: {output[:100]}",
            status=status,
        ),
        context=ContextBlock(),
        working_memory=WorkingMemory(findings=[output[:2000]]),
        handoff=Handoff(
            to_agent=incoming.agent_id,
            reason=f"reply_to:{incoming.id}",
        ),
    )
    try:
        await post_state(reply)
        logger.info("handoff_receiver: Antwort-State gepostet (reply_to:%s)", incoming.id)
    except Exception as e:
        logger.error("handoff_receiver: Antwort-State posten fehlgeschlagen: %s", e)


async def _post_error_reply(incoming: State, message: str) -> None:
    await _post_reply(incoming, message, "error")
