"""Datamining-Spiegel: laufende Aufgaben verfolgen und in fester Zeit herunterfahren (Task a11e9091).

Vorher: ``pool.close()`` wartete auf alle ausgeliehenen Verbindungen, Schreib- und Embedding-Aufgaben liefen
unbegrenzt weiter, neue starteten gegen einen schließenden Pool („pool is closing“) – der Shutdown dauerte auf
Prod 18 s länger als das 20-s-Zeitlimit von uvicorn. Was beim Abbruch verloren geht, holt ``_mirror_catchup``
beim nächsten Start nach.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

CLOSE_WAIT_S = 5.0     # laufende Schreibvorgänge höchstens so lange abwarten
POOL_CLOSE_S = 3.0     # danach Pool schließen; hängt das, Verbindungen hart trennen

tasks: "set[asyncio.Task]" = set()
closing = False


def track(coro) -> "asyncio.Task":
    """Aufgabe auf dem laufenden Loop starten und bis zu ihrem Ende merken."""
    task = asyncio.get_running_loop().create_task(coro)
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return task


async def drain(wait_s: float) -> int:
    """Laufende Aufgaben höchstens ``wait_s`` abwarten, den Rest abbrechen. Rückgabe: Zahl abgebrochener."""
    pending = [t for t in tasks if not t.done()]
    if not pending:
        return 0
    _done, still = await asyncio.wait(pending, timeout=wait_s)
    for t in still:
        t.cancel()
    if still:
        await asyncio.gather(*still, return_exceptions=True)
    return len(still)


async def close_pool(pool, wait_s: float) -> None:
    try:
        await asyncio.wait_for(pool.close(), timeout=wait_s)
    except Exception as e:  # noqa: BLE001 — Herunterfahren darf nicht hängen (auch TimeoutError)
        logger.warning("PG-Mirror: Pool schließt nicht sauber (%s) – Verbindungen werden getrennt",
                       e or "Zeitlimit")
        pool.terminate()
