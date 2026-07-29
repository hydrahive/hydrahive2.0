"""Session-Concurrency-Guard.

Verhindert dass zwei `runner.run()`-Aufrufe parallel auf der gleichen Session
laufen. Das passiert wenn:
- Der SSE-Stream abreißt (Browser-Refresh, Network-Hiccup) und der User dann
  einen neuen Prompt schickt während der Backend-Runner noch weiterläuft.
- Zwei verschiedene Clients zur gleichen Session gleichzeitig schicken.
- Voice + Chat-Route für die gleiche Session gleichzeitig getriggert werden.

Symptom ohne Guard: doppelte Iterationen in llm_calls (turn_in_session=1
zweimal), parallele Tool-Aufrufe, last-write-wins-Chaos in der Message-History.
Konkret beobachtet in der "analyse claude code"-Session mit ~46.5¢ verschenkt
durch den parallelen Sonnet-Call (Token-Audit #129).

Mechanismus: in-memory Set aktiver Session-IDs. Single-Process-Schutz —
wenn HH2 später mit mehreren Uvicorn-Workern läuft, müsste das auf
DB-basierten Status umgestellt werden (sessions.status='running').
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class SessionAlreadyRunning(RuntimeError):
    """Wird gehoben wenn ein zweiter Run für die gleiche Session startet."""
    def __init__(self, session_id: str):
        super().__init__(f"Session '{session_id}' läuft bereits")
        self.session_id = session_id


_active: set[str] = set()
_lock = asyncio.Lock()

# Task-Registry für entkoppelte Runs: hält die asyncio.Task-Referenz je Session,
# damit ein laufender Run gezielt gestoppt werden kann — auch wenn die
# auslösende HTTP-Verbindung (Browser) längst weg ist.
_tasks: dict[str, "asyncio.Task"] = {}


def register_task(session_id: str, task: "asyncio.Task") -> None:
    """Registriert den Run-Task einer Session (für gezieltes Stop/Cancel)."""
    _tasks[session_id] = task


def unregister_task(session_id: str) -> None:
    """Entfernt den Run-Task (im finally des Runs aufrufen)."""
    _tasks.pop(session_id, None)


def get_task(session_id: str) -> "asyncio.Task | None":
    return _tasks.get(session_id)


def cancel(session_id: str) -> bool:
    """Stoppt den laufenden Run-Task einer Session. True wenn ein Task
    gefunden und gecancelt wurde. Der Task räumt sich selbst im finally auf
    (unregister + Guard-Release)."""
    task = _tasks.get(session_id)
    if task is None or task.done():
        return False
    task.cancel()
    logger.info("Run-Task cancel() angefordert: %s", session_id)
    return True


@asynccontextmanager
async def session_run_guard(session_id: str) -> AsyncIterator[None]:
    """Acquire-or-fail guard. Bei laufendem Run → SessionAlreadyRunning."""
    async with _lock:
        if session_id in _active:
            raise SessionAlreadyRunning(session_id)
        _active.add(session_id)
        logger.debug("Session-Guard acquired: %s (active=%d)", session_id, len(_active))
    try:
        yield
    finally:
        async with _lock:
            _active.discard(session_id)
            logger.debug("Session-Guard released: %s (active=%d)", session_id, len(_active))


def is_running(session_id: str) -> bool:
    """Read-only Check (für Tests/Diagnose). Nicht race-safe — nur Snapshot.

    Läuft = im Guard-Set ODER ein noch nicht beendeter Run-Task registriert.
    (Der entkoppelte Task registriert sich; der Guard schützt den kritischen
    Abschnitt — beide zusammen ergeben den Live-Status.)
    """
    if session_id in _active:
        return True
    task = _tasks.get(session_id)
    return task is not None and not task.done()


def active_count() -> int:
    return len(_active)


def force_release(session_id: str) -> bool:
    """Notfall: Lock freigeben (z.B. von Admin-UI). Returnt True wenn entfernt."""
    if session_id in _active:
        _active.discard(session_id)
        logger.warning("Session-Guard force-released: %s", session_id)
        return True
    return False
