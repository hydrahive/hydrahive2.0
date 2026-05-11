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
    """Read-only Check (für Tests/Diagnose). Nicht race-safe — nur Snapshot."""
    return session_id in _active


def active_count() -> int:
    return len(_active)


def force_release(session_id: str) -> bool:
    """Notfall: Lock freigeben (z.B. von Admin-UI). Returnt True wenn entfernt."""
    if session_id in _active:
        _active.discard(session_id)
        logger.warning("Session-Guard force-released: %s", session_id)
        return True
    return False
