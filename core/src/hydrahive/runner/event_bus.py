"""Session-Event-Bus — lückenloser Live-Event-Stream pro Session.

Fundament für entkoppelte Runs mit flüssigem Token-Streaming: Der entkoppelte
Run ist der EINZIGE Producer und publisht jedes runner-Event mit fortlaufender
Sequenznummer (`seq`). Consumer (Sende-Stream UND Reconnect-Stream) lesen ab
ihrem Cursor weiter — kein Token geht verloren, auch wenn ein Client mitten im
Lauf neu verbindet.

Ringpuffer je Session puffert die letzten N Events für kurze Verbindungslücken.
Ist der Cursor rausgefallen (has_gap), lädt der Client einmalig aus der DB nach
und steigt am aktuellen seq wieder ein.

Single-Process/Single-Worker (wie das übrige Concurrency-System). Bei Multi-
Worker müsste der Bus über einen externen Broker (Redis/PG-LISTEN) laufen.
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import AsyncIterator

_DEFAULT_CAPACITY = 2000


class _SessionChannel:
    def __init__(self, capacity: int) -> None:
        self.seq = 0
        self.buffer: deque[tuple[int, dict]] = deque(maxlen=capacity)
        self.subscribers: set[asyncio.Queue] = set()
        self.closed = False


class SessionEventBus:
    def __init__(self, capacity: int = _DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._channels: dict[str, _SessionChannel] = {}

    def _channel(self, session_id: str) -> _SessionChannel:
        ch = self._channels.get(session_id)
        if ch is None:
            ch = _SessionChannel(self._capacity)
            self._channels[session_id] = ch
        return ch

    # ── Producer ──────────────────────────────────────────────────────────
    def open(self, session_id: str) -> None:
        """Startet einen frischen Kanal für einen neuen Run (seq beginnt bei 0)."""
        self._channels[session_id] = _SessionChannel(self._capacity)

    def publish(self, session_id: str, event: dict) -> int:
        """Hängt ein Event an, vergibt die nächste seq, verteilt an Subscriber."""
        ch = self._channel(session_id)
        ch.seq += 1
        item = (ch.seq, event)
        ch.buffer.append(item)
        for q in list(ch.subscribers):
            try:
                q.put_nowait(item)
            except asyncio.QueueFull:
                pass  # Subscriber-Queue ist großzügig; Overflow -> Gap-Recovery
        return ch.seq

    def close(self, session_id: str) -> None:
        """Signalisiert das Run-Ende: alle Subscriber-Iteratoren enden sauber."""
        ch = self._channels.get(session_id)
        if ch is None:
            return
        ch.closed = True
        for q in list(ch.subscribers):
            try:
                q.put_nowait(None)  # Sentinel = Ende
            except asyncio.QueueFull:
                pass

    # ── Consumer ──────────────────────────────────────────────────────────
    def latest_seq(self, session_id: str) -> int:
        ch = self._channels.get(session_id)
        return ch.seq if ch else 0

    def has_gap(self, session_id: str, after_seq: int) -> bool:
        """True, wenn Events nach after_seq bereits aus dem Puffer gefallen sind
        (der Client also eine Lücke hätte und aus der DB nachladen muss)."""
        ch = self._channels.get(session_id)
        if ch is None:
            return after_seq < 0
        if after_seq >= ch.seq:
            return False
        oldest = ch.buffer[0][0] if ch.buffer else ch.seq + 1
        # lückenlos vorhanden ist alles ab (oldest). Verpasst der Client etwas
        # zwischen after_seq+1 und oldest-1, ist das ein Gap.
        return (after_seq + 1) < oldest

    async def subscribe(
        self, session_id: str, after_seq: int = 0
    ) -> AsyncIterator[tuple[int, dict]]:
        """Liefert Events ab `after_seq`+1: erst die gepufferten (Backlog),
        dann live, bis der Run schließt."""
        ch = self._channel(session_id)
        q: asyncio.Queue = asyncio.Queue(maxsize=10000)
        ch.subscribers.add(q)
        try:
            # 1) Backlog aus dem Puffer (verpasste Events nachliefern)
            for seq, ev in list(ch.buffer):
                if seq > after_seq:
                    yield seq, ev
                    after_seq = seq
            # Wenn der Run schon geschlossen ist und nichts Neues kommt: Ende.
            if ch.closed and ch.seq <= after_seq:
                return
            # 2) Live-Events
            while True:
                item = await q.get()
                if item is None:  # close-Sentinel
                    return
                seq, ev = item
                if seq > after_seq:  # doppelte aus Backlog-Überlappung meiden
                    yield seq, ev
                    after_seq = seq
        finally:
            ch.subscribers.discard(q)


# Prozessweiter Standard-Bus (ein Producer je Session, viele Consumer).
bus = SessionEventBus()
