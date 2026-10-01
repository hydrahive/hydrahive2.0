"""Wartet auf das Ergebnis eines Hintergrund-Auftrags und stößt die Zustellung an.

Drei Wege führen zum Abschluss, der erste gewinnt (delegations.complete_if_running):
1. handoff_receiver schreibt das Ergebnis direkt (gleicher Prozess, Normalfall)
2. AgentLink-Antwort löst die Future (auch für den Fall, dass 1. fehlt)
3. Frist abgelaufen → 'timeout'

Die DB wird alle POLL_SECONDS geprüft. So endet das Warten auch dann, wenn die
AgentLink-Antwort verloren geht. Seit 15.09. war das 34-mal der Fall, der
Auftraggeber hing danach volle 10 min.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from hydrahive.agentlink import cancel_pending
from hydrahive.agentlink.protocol import State
from hydrahive.db import delegations as delegations_db
from hydrahive.runner import delegation_delivery
from hydrahive.runner._handoff_reply import bounded_reply

logger = logging.getLogger(__name__)

POLL_SECONDS = 15.0
_tasks: dict[str, asyncio.Task] = {}


def _remaining(deadline_iso: str) -> float:
    deadline = datetime.fromisoformat(deadline_iso)
    return (deadline - datetime.now(timezone.utc)).total_seconds()


def result_from_state(response: State) -> tuple[str, str]:
    """AgentLink-Antwort → (status, Text). Spiegelt _ask_agent_helpers."""
    from hydrahive.agentlink.checkpoints import split_checkpoint_findings
    findings = response.working_memory.findings if response.working_memory else []
    visible, checkpoint = split_checkpoint_findings(findings)
    text = "\n".join(visible) or (response.task.description if response.task else "")
    proto = response.task.status if response.task else "blocked"
    if proto == "done":
        return "done", bounded_reply(text)
    return ("paused" if checkpoint else "error"), bounded_reply(text)


async def watch(delegation_id: str, fut: asyncio.Future) -> None:
    row = delegations_db.get(delegation_id)
    if row is None:
        return
    state_id = row["state_id"]
    try:
        while True:
            left = _remaining(row["deadline_at"])
            if left <= 0:
                delegations_db.complete_if_running(
                    delegation_id, "timeout",
                    f"Keine Antwort von {row['target_name']} innerhalb der Frist.",
                )
                break
            try:
                response = await asyncio.wait_for(asyncio.shield(fut), timeout=min(POLL_SECONDS, left))
            except asyncio.TimeoutError:
                current = delegations_db.get(delegation_id)
                if current is None or current["status"] != "running":
                    break  # Receiver/Abbruch war schneller
                continue
            except asyncio.CancelledError:
                if fut.cancelled():
                    break  # cancel_pending durch Abbruch
                raise
            status, text = result_from_state(response)
            delegations_db.complete_if_running(delegation_id, status, text)
            break
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Delegation %s: Watcher fehlgeschlagen", delegation_id)
        delegations_db.complete_if_running(delegation_id, "error", "Interner Fehler beim Warten auf das Ergebnis.")
    finally:
        cancel_pending(state_id)
        _tasks.pop(delegation_id, None)
    delegation_delivery.kick(row["session_id"])


def start(delegation_id: str, fut: asyncio.Future) -> asyncio.Task:
    task = asyncio.create_task(watch(delegation_id, fut), name=f"delegation-{delegation_id}")
    _tasks[delegation_id] = task
    return task


def active_count() -> int:
    return len(_tasks)
