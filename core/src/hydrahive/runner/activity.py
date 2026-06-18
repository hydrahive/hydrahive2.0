"""In-Memory-Registry laufender Agenten + globaler Broadcaster für die Pixel-Leiste.

Single-Process (wie runner/concurrency.py). Best-effort: ein verpasstes stop()
(Crash) wird vom TTL-Prune in snapshot() aufgeräumt."""
from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import asdict, dataclass

_TTL_S = 900.0


@dataclass
class AgentActivity:
    session_id: str
    agent_id: str
    name: str
    owner: str
    project_id: str | None
    current_tool: str | None
    started_at: float


_active: dict[str, AgentActivity] = {}
_lock = threading.Lock()


class _Broadcaster:
    """Globaler Single-Channel-Fan-out (Muster: api/_session_broadcast.py)."""

    def __init__(self) -> None:
        self._subs: set[asyncio.Queue] = set()
        self._slock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=8)
        with self._slock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._slock:
            self._subs.discard(q)

    def publish(self) -> None:
        with self._slock:
            queues = list(self._subs)
        for q in queues:
            try:
                q.put_nowait(1)
            except asyncio.QueueFull:
                pass  # Signal idempotent — verpasstes wird vom nächsten miterledigt


broadcaster = _Broadcaster()


def start(session_id: str, agent: dict, owner: str, project_id: str | None) -> None:
    with _lock:
        _active[session_id] = AgentActivity(
            session_id=session_id, agent_id=agent.get("id", ""),
            name=agent.get("name", ""), owner=owner, project_id=project_id,
            current_tool=None, started_at=time.time(),
        )
    broadcaster.publish()


def set_tool(session_id: str, tool: str | None) -> None:
    with _lock:
        a = _active.get(session_id)
        if a is None:
            return
        a.current_tool = tool
    broadcaster.publish()


def stop(session_id: str) -> None:
    with _lock:
        existed = _active.pop(session_id, None)
    if existed is not None:
        broadcaster.publish()


def snapshot(owner: str) -> list[dict]:
    now = time.time()
    with _lock:
        stale = [sid for sid, a in _active.items() if now - a.started_at > _TTL_S]
        for sid in stale:
            _active.pop(sid, None)
        return [asdict(a) for a in _active.values() if a.owner == owner]
