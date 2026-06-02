"""Live-Sync v1: Per-Session-Broadcaster für SSE-Subscriber.

Mehrere Geräte/Tabs derselben Session abonnieren je eine Queue. Während ein Lauf
läuft, broadcastet die Sende-Route leichte Pings in den Session-Kanal; die
passiven Clients laden bei Ping nach (debounced). Nur fan-out + Cleanup —
Presence/Replay (Multi-User) wäre eine spätere Stufe.

In-Memory, Single-Process. threading.Lock schützt die Dicts auch gegen FastAPIs
Thread-Pool-Ausführung sync-Routen; die Methoden bleiben synchron (keine awaits
zwischen Mutationen).
"""
from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

_DEFAULT_MAXSIZE = 32


class SessionBroadcaster:
    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """Neuer Client → eigene Queue, die der SSE-Endpoint liest."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._maxsize)
        with self._lock:
            self._subs.setdefault(session_id, set()).add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            subs = self._subs.get(session_id)
            if subs is not None:
                subs.discard(queue)
                if not subs:
                    del self._subs[session_id]

    def broadcast(self, session_id: str, payload: str) -> None:
        """Ping an alle Clients der Session. Volle Queue (langsamer Client) →
        ältesten Eintrag droppen und neuen einsetzen; Pings sind idempotent
        (ein verpasster Ping wird vom nächsten mit-erledigt)."""
        with self._lock:
            queues = list(self._subs.get(session_id, ()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()       # ältesten droppen
                    q.put_nowait(payload)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def subscriber_count(self, session_id: str) -> int:
        with self._lock:
            return len(self._subs.get(session_id, ()))


# Prozess-weiter Singleton — Sende-Route broadcastet, Stream-Route abonniert.
broadcaster = SessionBroadcaster()
