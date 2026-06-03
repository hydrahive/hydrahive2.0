"""Team-Chat RoomBroadcaster: SSE-Fanout pro room_id.

Mehrere Frontends/Tabs desselben Rooms abonnieren je eine Queue. Beim Eingang
einer neuen Nachricht broadcastet die Post-Route in den Room-Kanal; alle
Subscriber empfangen das Payload und können es direkt rendern.

In-Memory, Single-Process. threading.Lock schützt die Dicts auch gegen FastAPIs
Thread-Pool-Ausführung sync-Routen; die Methoden bleiben synchron (keine awaits
zwischen Mutationen).

Gespiegelt von api/_session_broadcast.py — nur session_id → room_id umbenannt.
"""
from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

_DEFAULT_MAXSIZE = 32


class RoomBroadcaster:
    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def subscribe(self, room_id: str) -> asyncio.Queue:
        """Neuer Client → eigene Queue, die der SSE-Endpoint liest."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._maxsize)
        with self._lock:
            self._subs.setdefault(room_id, set()).add(queue)
        return queue

    def unsubscribe(self, room_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            subs = self._subs.get(room_id)
            if subs is not None:
                subs.discard(queue)
                if not subs:
                    del self._subs[room_id]

    def broadcast(self, room_id: str, payload: str) -> None:
        """Nachricht an alle Clients des Rooms. Volle Queue (langsamer Client) →
        ältesten Eintrag droppen und neuen einsetzen; Nachrichten sind
        sequenziell, daher wird bei Überlauf der älteste Eintrag geopfert."""
        with self._lock:
            queues = list(self._subs.get(room_id, ()))
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()       # ältesten droppen
                    q.put_nowait(payload)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def subscriber_count(self, room_id: str) -> int:
        with self._lock:
            return len(self._subs.get(room_id, ()))


# Prozess-weiter Singleton — Post-Route broadcastet, Stream-Route abonniert.
room_broadcaster = RoomBroadcaster()
