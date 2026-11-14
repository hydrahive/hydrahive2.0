"""Registry laufender eingehender Handoff-Tasks für den Graceful Shutdown
(Spec delegation-reliability.md 3.1).

`api/lifespan.py` startet für jeden eingehenden Handoff
`asyncio.create_task(handoff_receiver.handle(event), ...)` fire-and-forget — beim
Server-Stopp wurde dieser Task bisher einfach vom Event-Loop abgeschnitten, ohne dass
der CancelledError-Pfad in `handoff_receiver._run_and_reply` (Checkpoint statt
Totalverlust, 3.2) überhaupt eine Chance bekam zu laufen. `register()`/`shutdown()`
machen diese Tasks für den Shutdown sichtbar und gezielt abwartbar.

Muster wie `runner/delegation_watch.py` (`_tasks`-Dict), bewusst separat: andere
Lebensdauer (ein Handoff-Task pro eingehendem Auftrag, nicht pro ausgehender
Delegation) und anderer Zweck (Shutdown-Signal geben, nicht auf ein Ergebnis warten).
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_tasks: dict[str, asyncio.Task] = {}


def register(key: str, task: asyncio.Task) -> None:
    _tasks[key] = task
    task.add_done_callback(lambda _t: _tasks.pop(key, None))


def active_count() -> int:
    return len(_tasks)


async def shutdown(*, timeout: float = 10.0) -> None:
    """Cancelt alle laufenden Handoff-Tasks und wartet kurz, bis ihr
    CancelledError-Pfad (Checkpoint posten, DB-Status setzen) durchgelaufen ist.
    Best-effort: nach `timeout` wird nicht länger gewartet, der Prozess beendet
    trotzdem (ein hängender Checkpoint-Post darf den Deploy nicht blockieren)."""
    tasks = list(_tasks.values())
    if not tasks:
        return
    for task in tasks:
        task.cancel()
    await asyncio.wait(tasks, timeout=timeout)


def clear_for_test() -> None:
    _tasks.clear()
