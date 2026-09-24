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
from dataclasses import dataclass

from hydrahive.agentlink.checkpoints import checkpoint_finding
from hydrahive.agentlink.client import get_state
from hydrahive.agentlink.protocol import State, WSEvent
from hydrahive.db import agent_handoffs as db_agent_handoffs
from hydrahive.runner._handoff_reply import (
    post_error_reply as _post_error_reply,
    post_reply as _post_reply,
)
from hydrahive.runner._handoff_setup import (
    HandoffSetupError,
    prepare_handoff,
    rollback_prepared,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RunFailure:
    message: str
    kind: str | None = None


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
    prepared = None
    try:
        prepared = prepare_handoff(state, target, reason)
        asyncio.create_task(
            _run_and_reply(
                state, prepared.session_id, prepared.handoff_id,
                run_timeout=prepared.timeout_seconds, resumed=prepared.resumed,
            ),
            name=f"handoff-{state.id}",
        )
    except HandoffSetupError as exc:
        logger.warning("handoff_receiver: Handoff-Setup abgelehnt: %s", exc)
        await _post_error_reply(state, str(exc))
        return
    except Exception:
        if prepared is not None:
            rollback_prepared(prepared)
        logger.exception("handoff_receiver: Handoff konnte nicht geplant werden")
        await _post_error_reply(state, "Handoff konnte nicht sicher gestartet werden")
        return
    logger.info(
        "handoff_receiver: eingehender Task von '%s' → Agent '%s' (Session %s)",
        state.agent_id, target["id"], prepared.session_id,
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


async def _consume_run(
    session_id: str, user_input: str, output_parts: list[str],
) -> RunFailure | None:
    """Run the agent and preserve structured runner failure metadata."""
    from hydrahive.runner import runner
    from hydrahive.runner.concurrency import session_run_guard
    from hydrahive.runner.events import Error

    async with session_run_guard(session_id):
        async for ev in runner.run(session_id, user_input):
            if hasattr(ev, "text"):
                output_parts.append(ev.text)
            elif isinstance(ev, Error):
                metadata = ev.metadata if isinstance(ev.metadata, dict) else {}
                return RunFailure(ev.message, metadata.get("kind"))
    return None


async def _run_and_reply(
    state: State,
    session_id: str,
    handoff_db_id: str,
    *,
    run_timeout: int | None = None,
    resumed: bool = False,
) -> None:
    from hydrahive.runner.concurrency import SessionAlreadyRunning

    user_input = "weiter" if resumed else _build_user_input(state)
    output_parts: list[str] = []
    failure: RunFailure | None = None

    effective_timeout = run_timeout or settings.agentlink_run_timeout
    try:
        async with asyncio.timeout(effective_timeout):
            failure = await _consume_run(session_id, user_input, output_parts)
    except TimeoutError:
        # Run lief länger als der Worker tolerieren soll → terminale Fehler-Antwort,
        # damit der Auftraggeber nicht ins Caller-Timeout läuft und kein in_progress-
        # Zombie zurückbleibt.
        failure = RunFailure(
            f"Timeout nach {effective_timeout}s — Aufgabe nicht abgeschlossen",
        )
        logger.warning("handoff_receiver: Run-Timeout für Session %s", session_id)
    except SessionAlreadyRunning:
        failure = RunFailure("Session läuft bereits — handoff ignoriert")
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
        failure = RunFailure(str(e))
        logger.exception("handoff_receiver: Runner-Fehler für Session %s", session_id)

    output = "".join(output_parts)
    is_checkpoint = bool(failure and failure.kind == "max_iterations")
    if failure:
        label = "Pausiert" if is_checkpoint else "Terminaler Fehler"
        output = f"{output}\n\n{label}: {failure.message}" if output else failure.message
    elif not output:
        output = "Kein Output"
    status = "paused" if is_checkpoint else "error" if failure else "done"
    checkpoint = None
    if is_checkpoint:
        checkpoint = checkpoint_finding(
            resume_token=handoff_db_id,
            session_id=session_id,
            remaining_work="Begonnenen Auftrag abschließen und Ergebnis verifizieren.",
        )

    # Activate a checkpoint before publishing its capability token, otherwise an
    # immediate resume can race against a still-"running" DB row.
    db_agent_handoffs.update_status(handoff_db_id, status)
    delivered = await _post_reply(state, output, status, checkpoint=checkpoint)
    if status == "paused" and delivered is False:
        # No caller received the capability, so do not retain an unreachable token.
        db_agent_handoffs.update_status(handoff_db_id, "error")


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
