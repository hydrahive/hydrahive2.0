"""In-Memory-Registry laufender Agenten + globaler Broadcaster für Pixel-Leiste und Agenten-Büro.

Single-Process (wie runner/concurrency.py). Best-effort: ein verpasstes stop()
(Crash) wird vom TTL-Prune in snapshot() aufgeräumt.

Erweiterung Agenten-Büro (Spec agent-office.md §1, 14.11.2026): zusätzlich zum reinen `current_tool`
jetzt auch die Delegations-Hierarchie (`parent_session_id`/`delegation_id`), der Fortschritt
(`iteration`/`max_iterations`), eine Restzeit (`deadline_at`) und eine kurze, geleakte Zusammenfassung
des letzten Tool-Ergebnisses (`last_tool_result_summary`, hart auf 120 Zeichen begrenzt — keine
Nutzdaten über die Kurzfassung hinaus).
"""
from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import asdict, dataclass

_TTL_S = 900.0
_SUMMARY_MAX_CHARS = 120


@dataclass
class AgentActivity:
    session_id: str
    agent_id: str
    name: str
    owner: str
    project_id: str | None
    current_tool: str | None
    started_at: float
    parent_session_id: str | None = None
    delegation_id: str | None = None
    iteration: int = 0
    max_iterations: int = 0
    deadline_at: float | None = None
    last_tool_result_summary: str = ""


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


def start(
    session_id: str, agent: dict, owner: str, project_id: str | None,
    *, parent_session_id: str | None = None, delegation_id: str | None = None,
    max_iterations: int = 0, deadline_at: float | None = None,
) -> None:
    with _lock:
        _active[session_id] = AgentActivity(
            session_id=session_id, agent_id=agent.get("id", ""),
            name=agent.get("name", ""), owner=owner, project_id=project_id,
            current_tool=None, started_at=time.time(),
            parent_session_id=parent_session_id, delegation_id=delegation_id,
            max_iterations=max_iterations, deadline_at=deadline_at,
        )
    broadcaster.publish()


def set_tool(session_id: str, tool: str | None, *, result_summary: str | None = None) -> None:
    """Werkzeug der laufenden Iteration setzen und die Iteration hochzählen (ein Aufruf je Runde).

    `result_summary`: Kurzfassung des VORHERIGEN Tool-Ergebnisses (None = unverändert lassen, nicht
    löschen — die UI zeigt sonst kurz nichts zwischen zwei Aufrufen)."""
    with _lock:
        a = _active.get(session_id)
        if a is None:
            return
        a.current_tool = tool
        a.iteration += 1
        if result_summary is not None:
            a.last_tool_result_summary = result_summary[:_SUMMARY_MAX_CHARS]
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
