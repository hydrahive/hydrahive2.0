"""Empfänger für eingehende AgentLink-Handoffs.

Wenn ein anderer Agent einen Task via AgentLink an uns schickt, muss HH2:
  1. Den eingehenden State laden
  2. Den adressierten Agenten bestimmen (state.handoff.to_agent → lokal suchen)
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

    # Interne Handoffs kodieren die echte Ziel-Agent-ID im reason-Präfix:
    # "hh-target:<uuid>|hh-task: ..." — extra{} wird von post_state nicht gesendet.
    reason = (state.handoff.reason or "") if state.handoff else ""
    to_agent_id: str | None = None
    if reason.startswith("hh-target:"):
        to_agent_id = reason.split("|", 1)[0].removeprefix("hh-target:")
    elif state.handoff:
        to_agent_id = state.handoff.to_agent
    target = _find_target_agent(to_agent_id)
    if not target:
        logger.warning(
            "handoff_receiver: to_agent=%r nicht adressiert/unbekannt/inaktiv — Handoff abgelehnt "
            "(kein Master-Fallback, Issue #177)",
            to_agent_id,
        )
        await _post_error_reply(state, "Kein gültiger Ziel-Agent adressiert")
        return

    _warn_if_unconfirmed(target)
    owner = target.get("owner") or "admin"
    session = sessions_db.create(
        agent_id=target["id"],
        user_id=owner,
        project_id=target.get("project_id"),
        title=(state.task.description or "AgentLink-Task")[:80],
        metadata={"source": "agentlink", "incoming_state_id": state.id},
    )

    handoff_record = db_agent_handoffs.create(
        incoming_state_id=state.id or "",
        from_agent=state.agent_id,
        agent_id=target["id"],
        session_id=session.id,
    )

    asyncio.create_task(
        _run_and_reply(state, session.id, handoff_record["id"]),
        name=f"handoff-{state.id}",
    )
    logger.info(
        "handoff_receiver: eingehender Task von '%s' → Agent '%s' (Session %s)",
        state.agent_id, target["id"], session.id,
    )


def _find_target_agent(to_agent_id: str | None) -> dict | None:
    """Gibt den explizit adressierten, aktiven Agenten zurück — sonst None.

    KEIN Fallback auf den Admin-Master (Issue #177): ein eingehender Handoff
    von außen darf niemals auf den unrestricted Master eskalieren. Unadressierte,
    unbekannte oder inaktive Handoffs werden abgelehnt."""
    from hydrahive.agents import config as agent_config
    if not to_agent_id:
        return None
    agent = agent_config.get(to_agent_id)
    if agent and agent.get("status") == "active":
        logger.debug("handoff_receiver: Ziel-Agent '%s' lokal gefunden", to_agent_id)
        return agent
    return None


def _warn_if_unconfirmed(target: dict) -> None:
    """Macht sichtbar, wenn ein AgentLink-Handoff einen Agenten trifft, der
    Tools ohne Bestätigung ausführt (auto-exec). Architektur-Empfehlung:
    AgentLink-erreichbare Agenten mit require_tool_confirm=True konfigurieren."""
    if not target.get("require_tool_confirm", False):
        logger.warning(
            "handoff_receiver: Ziel-Agent '%s' läuft mit require_tool_confirm=False — "
            "AgentLink-Handoff führt Tools ohne Bestätigung aus",
            target.get("id"),
        )


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


async def _consume_run(session_id: str, user_input: str, output_parts: list[str]) -> str | None:
    """Führt den Agent-Run aus und sammelt Text-Output in `output_parts`.
    Returnt eine Fehlermeldung wenn der Runner ein Error-Event liefert, sonst None.
    Ausgelagert, damit `_run_and_reply` sie in ein asyncio.timeout kapseln kann."""
    from hydrahive.runner import runner
    from hydrahive.runner.concurrency import session_run_guard
    from hydrahive.runner.events import Error

    async with session_run_guard(session_id):
        async for ev in runner.run(session_id, user_input):
            if hasattr(ev, "text"):
                output_parts.append(ev.text)
            elif isinstance(ev, Error):
                return ev.message
    return None


async def _run_and_reply(state: State, session_id: str, handoff_db_id: str) -> None:
    from hydrahive.runner.concurrency import SessionAlreadyRunning

    user_input = _build_user_input(state)
    output_parts: list[str] = []
    error_msg: str | None = None

    try:
        async with asyncio.timeout(settings.agentlink_run_timeout):
            error_msg = await _consume_run(session_id, user_input, output_parts)
    except TimeoutError:
        # Run lief länger als der Worker tolerieren soll → terminale Fehler-Antwort,
        # damit der Auftraggeber nicht ins Caller-Timeout läuft und kein in_progress-
        # Zombie zurückbleibt.
        error_msg = (
            f"Timeout nach {settings.agentlink_run_timeout}s — Aufgabe nicht abgeschlossen"
        )
        logger.warning("handoff_receiver: Run-Timeout für Session %s", session_id)
    except SessionAlreadyRunning:
        error_msg = "Session läuft bereits — handoff ignoriert"
        logger.warning("handoff_receiver: Session %s läuft bereits — skip", session_id)
    except asyncio.CancelledError:
        # Worker-Shutdown/Reload: best-effort terminale Antwort posten, dann
        # re-raise. Ohne das bliebe der State ewig in_progress (Subagent-Zombie).
        logger.warning(
            "handoff_receiver: Run für Session %s abgebrochen (Shutdown) — poste Fehler-Antwort",
            session_id,
        )
        try:
            await asyncio.shield(_post_reply(state, "Abgebrochen (Worker-Shutdown)", "error"))
            db_agent_handoffs.update_status(handoff_db_id, "error")
        except Exception:
            logger.exception("handoff_receiver: Fehler-Antwort bei Cancel fehlgeschlagen")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception("handoff_receiver: Runner-Fehler für Session %s", session_id)

    output = "".join(output_parts) if output_parts else (error_msg or "Kein Output")
    status = "error" if error_msg else "done"

    await _post_reply(state, output, status)
    db_agent_handoffs.update_status(handoff_db_id, status)


def reconcile_orphaned_handoffs() -> int:
    """Beim Start: alle noch auf 'running' stehenden Handoffs auf 'error' setzen.

    Solche Einträge sind durch einen früheren Worker-Tod (Crash, --reload, SIGKILL)
    verwaist — der zugehörige Run wurde nie beendet und nie beantwortet. Ohne
    Reconciliation blieben sie ewig als in_progress-Zombie hängen."""
    orphans = db_agent_handoffs.list_active()
    for h in orphans:
        db_agent_handoffs.update_status(h["id"], "error")
    if orphans:
        logger.warning(
            "handoff_receiver: %d verwaiste Handoff(s) beim Start auf 'error' gesetzt",
            len(orphans),
        )
    return len(orphans)


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
            to_agent=settings.agentlink_agent_id,
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
