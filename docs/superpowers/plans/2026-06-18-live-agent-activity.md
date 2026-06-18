# Live-Agent-Aktivität (Pixel-Leiste) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Die Pixel-Männchen-Leiste zeigt echten Live-Status pro Agent (Backend-Aktivitäts-Feed via SSE) statt aus der Nachrichten-Historie abgeleitet; delegierte Spezialisten animieren live und verschwinden wenn idle. Umschalter „Chat ↔ Alle".

**Architecture:** In-Memory-Aktivitäts-Registry (`runner/activity.py`), vom Runner bei Start/Tool/Ende aktualisiert, über globalen SSE-Kanal gepusht; Frontend-Hook speist den Monitor.

**Tech Stack:** Python 3.12 / FastAPI / pytest (Backend, TDD). React+TS / vite (Frontend, verifiziert via `tsc -b` + `eslint` — kein JS-Test-Runner vorhanden).

## Global Constraints

- Max ~200 Zeilen/Datei, eine Verantwortung. Single-Process (wie `concurrency.py`).
- Backend TDD zuerst (pytest aus Repo-Root: `.venv/bin/python3 -m pytest`).
- Frontend: nach Edits `cd frontend && npx tsc -b` (Typecheck) + `npx eslint .` grün.
- Owner-Filter: SSE zeigt nur Agenten des eingeloggten Users.
- Commits gebündelt am Ende (Tills Vorgabe).

---

### Task 1: Aktivitäts-Registry + Broadcaster

**Files:**
- Create: `core/src/hydrahive/runner/activity.py`
- Test: `core/tests/test_agent_activity.py`

**Interfaces:**
- Produces: `start(session_id, agent: dict, owner: str, project_id: str|None)`, `set_tool(session_id, tool: str|None)`, `stop(session_id)`, `snapshot(owner: str) -> list[dict]`, `broadcaster` (subscribe/unsubscribe/publish). Snapshot-Einträge: `{session_id, agent_id, name, owner, project_id, current_tool, started_at}`. TTL 900s.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_agent_activity.py
import time
from hydrahive.runner import activity


def _agent():
    return {"id": "a1", "name": "Reviewer"}


def test_start_appears_in_owner_snapshot():
    activity.stop("s1")  # sauberer Start
    activity.start("s1", _agent(), owner="u", project_id="P")
    snap = activity.snapshot("u")
    assert any(e["session_id"] == "s1" and e["name"] == "Reviewer" and e["project_id"] == "P" for e in snap)
    assert activity.snapshot("other") == []
    activity.stop("s1")


def test_set_tool_and_stop():
    activity.start("s2", _agent(), owner="u", project_id=None)
    activity.set_tool("s2", "shell_exec")
    assert activity.snapshot("u")[0]["current_tool"] == "shell_exec"
    activity.stop("s2")
    assert all(e["session_id"] != "s2" for e in activity.snapshot("u"))


def test_ttl_prunes_stale(monkeypatch):
    activity.start("s3", _agent(), owner="u", project_id=None)
    # started_at künstlich altern
    with activity._lock:
        activity._active["s3"].started_at = time.time() - 1000
    assert all(e["session_id"] != "s3" for e in activity.snapshot("u"))


def test_broadcaster_wakes_subscriber():
    q = activity.broadcaster.subscribe()
    try:
        activity.start("s4", _agent(), owner="u", project_id=None)
        assert not q.empty()
    finally:
        activity.broadcaster.unsubscribe(q)
        activity.stop("s4")
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity.py -q`
Expected: FAIL (`ModuleNotFoundError: ... runner.activity`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/runner/activity.py
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
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity.py -q`
Expected: PASS (4 passed).

---

### Task 2: Runner-Hooks (start/set_tool) + stop via session_end

**Files:**
- Modify: `core/src/hydrahive/runner/runner.py` (nach `session_start(...)` → `activity.start`; vor `process_tool_uses` → `activity.set_tool`)
- Modify: `core/src/hydrahive/tools/_sessions.py` (`session_end` → `activity.stop`)
- Test: `core/tests/test_agent_activity_hooks.py`

**Interfaces:**
- Consumes: `activity.start/set_tool/stop` (Task 1).
- Produces: jeder `runner.run` registriert/aktualisiert/entfernt Aktivität; `session_end` ruft `activity.stop`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_agent_activity_hooks.py
from hydrahive.tools import _sessions
from hydrahive.runner import activity


def test_session_end_stops_activity(monkeypatch):
    activity.start("sess-x", {"id": "a1", "name": "X"}, owner="u", project_id=None)
    assert activity.snapshot("u")
    _sessions.session_end("a1", "sess-x", status="completed")
    assert all(e["session_id"] != "sess-x" for e in activity.snapshot("u"))
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity_hooks.py -q`
Expected: FAIL (session_end räumt Aktivität noch nicht ab).

- [ ] **Step 3: Implement**

In `core/src/hydrahive/tools/_sessions.py`, am Ende von `session_end(...)` ergänzen (lazy import gegen Zyklen):
```python
    from hydrahive.runner import activity
    activity.stop(session_id)
```

In `core/src/hydrahive/runner/runner.py` direkt nach dem `session_start(...)`-Block (nach Zeile ~96):
```python
    from hydrahive.runner import activity
    activity.start(session_id, agent, owner=session.user_id, project_id=active_project_id)
```

In `core/src/hydrahive/runner/runner.py` unmittelbar vor `async for item in process_tool_uses(`:
```python
        activity.set_tool(session_id, tool_uses[-1].get("name") if tool_uses else None)
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity_hooks.py core/tests/test_agent_activity.py -q`
Expected: PASS.

---

### Task 3: SSE-Endpoint `/api/agents/activity/stream`

**Files:**
- Create: `core/src/hydrahive/api/routes/agent_activity.py`
- Modify: `core/src/hydrahive/api/main.py` (Router mounten)
- Test: `core/tests/test_agent_activity_route.py`

**Interfaces:**
- Consumes: `activity.snapshot`, `activity.broadcaster`.
- Produces: `GET /api/agents/activity/stream` (auth) → SSE; initiale Owner-Momentaufnahme + bei jedem Broadcast neue.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_agent_activity_route.py
def test_stream_requires_auth(client):
    r = client.get("/api/agents/activity/stream")
    assert r.status_code == 401


def test_stream_sends_initial_owner_snapshot(client, auth_headers):
    from hydrahive.runner import activity
    activity.start("sess-r", {"id": "a1", "name": "Reviewer"}, owner="testuser", project_id="P")
    try:
        with client.stream("GET", "/api/agents/activity/stream", headers=auth_headers) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            for line in r.iter_lines():
                if line.startswith("data:"):
                    assert "Reviewer" in line
                    break
    finally:
        activity.stop("sess-r")
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity_route.py -q`
Expected: FAIL (404 / Route fehlt).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/api/routes/agent_activity.py
"""SSE-Feed laufender Agenten für die Pixel-Leiste (nur eigene Agenten)."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from hydrahive.api.middleware.auth import require_auth
from hydrahive.runner import activity

router = APIRouter(prefix="/api/agents/activity", tags=["agents"])


@router.get("/stream")
async def stream_activity(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> StreamingResponse:
    username, _role = auth
    queue = activity.broadcaster.subscribe()

    async def _events():
        try:
            yield f"data: {json.dumps(activity.snapshot(username))}\n\n"
            while True:
                try:
                    await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps(activity.snapshot(username))}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            activity.broadcaster.unsubscribe(queue)

    return StreamingResponse(
        _events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
```

In `core/src/hydrahive/api/main.py` den Router registrieren (neben den anderen `app.include_router(...)`-Zeilen):
```python
    from hydrahive.api.routes import agent_activity
    app.include_router(agent_activity.router)
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity_route.py -q`
Expected: PASS.

---

### Task 4: Frontend — Abo + Hook + reine Filterfunktion

**Files:**
- Modify: `frontend/src/features/chat/api.ts` (`subscribeAgentActivity`)
- Create: `frontend/src/features/chat/useAgentActivity.ts`
- Create: `frontend/src/features/chat/_pixelSelect.ts`

**Interfaces:**
- Produces:
  - `subscribeAgentActivity(onSnapshot: (a: ActivityEntry[]) => void, signal: AbortSignal): Promise<void>`
  - `useAgentActivity(enabled: boolean): { running: ActivityEntry[] }`
  - `selectPixelAgents(running, scope, activeAgentName, askTargets) -> { agentTools, activeAgents, doneAgents }`
  - `ActivityEntry = { session_id, agent_id, name, project_id, current_tool }`

- [ ] **Step 1: `subscribeAgentActivity` in api.ts** (Muster: `subscribeSession`)

```typescript
export interface ActivityEntry {
  session_id: string; agent_id: string; name: string
  project_id: string | null; current_tool: string | null
}

export async function subscribeAgentActivity(
  onSnapshot: (agents: ActivityEntry[]) => void,
  signal: AbortSignal,
): Promise<void> {
  const RECONNECT_MS = 1500
  while (!signal.aborted) {
    try {
      const token = useAuthStore.getState().token
      const res = await fetch("/api/agents/activity/stream", {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        signal,
      })
      if (!res.ok || !res.body) throw new Error(`activity ${res.status}`)
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const frames = buffer.split("\n\n")
        buffer = frames.pop() ?? ""
        for (const frame of frames) {
          const dataLine = frame.split("\n").find((l) => l.startsWith("data:"))
          if (dataLine) {
            try { onSnapshot(JSON.parse(dataLine.slice(5).trim()) as ActivityEntry[]) } catch { /* ignore */ }
          }
        }
      }
    } catch {
      if (signal.aborted) return
    }
    if (signal.aborted) return
    await new Promise((r) => setTimeout(r, RECONNECT_MS))
  }
}
```

- [ ] **Step 2: `useAgentActivity.ts`** — Abo + „done"-Nachklang (2,5 s)

```typescript
import { useEffect, useRef, useState } from "react"
import { subscribeAgentActivity, type ActivityEntry } from "./api"

const DONE_LINGER_MS = 2500

export function useAgentActivity(enabled: boolean): { running: ActivityEntry[]; doneNames: string[] } {
  const [running, setRunning] = useState<ActivityEntry[]>([])
  const [doneNames, setDoneNames] = useState<string[]>([])
  const prevNames = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!enabled) { setRunning([]); setDoneNames([]); prevNames.current = new Set(); return }
    const controller = new AbortController()
    void subscribeAgentActivity((agents) => {
      const names = new Set(agents.map((a) => a.name))
      const justDone = [...prevNames.current].filter((n) => !names.has(n))
      prevNames.current = names
      setRunning(agents)
      if (justDone.length) {
        setDoneNames((d) => [...new Set([...d, ...justDone])])
        justDone.forEach((n) =>
          setTimeout(() => setDoneNames((d) => d.filter((x) => x !== n)), DONE_LINGER_MS))
      }
    }, controller.signal)
    return () => controller.abort()
  }, [enabled])

  // Laufende Namen aus doneNames entfernen (wieder aktiv)
  const liveNames = new Set(running.map((a) => a.name))
  return { running, doneNames: doneNames.filter((n) => !liveNames.has(n)) }
}
```

- [ ] **Step 3: `_pixelSelect.ts`** — reine Ableitung der Monitor-Props

```typescript
import type { ActivityEntry } from "./api"

export interface PixelProps {
  agentTools: Record<string, string[]>
  activeAgents: string[]
  doneAgents: string[]
}

export function selectPixelAgents(
  running: ActivityEntry[],
  scope: "chat" | "all",
  activeAgentName: string | null,
  askTargets: string[],
  doneNames: string[],
): PixelProps {
  const targets = new Set(askTargets)
  const visible = scope === "all"
    ? running
    : running.filter((a) => a.name === activeAgentName || targets.has(a.name))
  const agentTools: Record<string, string[]> = {}
  for (const a of visible) agentTools[a.name] = a.current_tool ? [a.current_tool] : []
  const doneVisible = scope === "all"
    ? doneNames
    : doneNames.filter((n) => n === activeAgentName || targets.has(n))
  for (const n of doneVisible) if (!agentTools[n]) agentTools[n] = []
  return {
    agentTools,
    activeAgents: visible.map((a) => a.name),
    doneAgents: doneVisible,
  }
}
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: keine Fehler (ggf. ungenutzte Symbole erst nach Task 5 weg — dann hier nur die 3 neuen Dateien prüfen, finaler tsc in Task 6).

---

### Task 5: ChatPage-Verdrahtung + Monitor-Umschalter

**Files:**
- Modify: `frontend/src/features/chat/ChatPage.tsx` (Hook nutzen, `pixelScope`, `selectPixelAgents`; alte message-basierte `pixelData` ersetzen)
- Modify: `frontend/src/features/chat/AgentPixelMonitor.tsx` (Umschalter „Chat ↔ Alle")

**Interfaces:**
- Consumes: `useAgentActivity`, `selectPixelAgents`.

- [ ] **Step 1: ChatPage** — Hook + Scope + askTargets

In `ChatPage.tsx`: `const [pixelScope, setPixelScope] = useState<"chat" | "all">("chat")`.
`const { running, doneNames } = useAgentActivity(showPixelMonitor)`.
`askTargets` aus den `ask_agent`-Aufrufen der Session ableiten (Namen), dann:
```tsx
  const pixelData = useMemo(() => {
    const askTargets: string[] = []
    for (const msg of allMessages) {
      if (!Array.isArray(msg.content)) continue
      for (const block of msg.content) {
        if (block.type !== "tool_use" || (block as { name?: string }).name !== "ask_agent") continue
        const tid = ((block as { input?: { agent_id?: string } }).input?.agent_id ?? "")
        const found = agents.find(a => a.id === tid || a.name.toLowerCase().includes(tid.toLowerCase()))
        if (found?.name) askTargets.push(found.name)
        else if (tid) askTargets.push(tid)
      }
    }
    return selectPixelAgents(running, pixelScope, activeAgent?.name ?? null, askTargets, doneNames)
  }, [running, doneNames, pixelScope, activeAgent, agents, allMessages])
```
Den `AgentPixelMonitor`-Aufruf um `scope`/`onScope` erweitern:
```tsx
            <AgentPixelMonitor
              agentTools={pixelData.agentTools}
              activeAgents={pixelData.activeAgents}
              doneAgents={pixelData.doneAgents}
              scope={pixelScope}
              onScope={setPixelScope}
            />
```

- [ ] **Step 2: AgentPixelMonitor** — Umschalter

Props erweitern: `scope: "chat" | "all"; onScope: (s: "chat" | "all") => void`. Über dem Canvas einen kleinen Toggle rendern (zwei Buttons „Chat"/„Alle", aktiver hervorgehoben). `return null` nur wenn `agentTools` leer **und** scope === "chat" (im „Alle"-Modus auch leer anzeigen, damit der Umschalter erreichbar bleibt) — alternativ Toggle immer zeigen, Canvas nur bei Agenten.

- [ ] **Step 3: Typecheck + Lint**

Run: `cd frontend && npx tsc -b && npx eslint src/features/chat`
Expected: grün.

---

### Task 6: Gesamt-Verifikation

- [ ] **Step 1: Backend-Tests**

Run: `.venv/bin/python3 -m pytest core/tests/test_agent_activity.py core/tests/test_agent_activity_hooks.py core/tests/test_agent_activity_route.py core/tests/test_handoff_receiver_resilience.py -q`
Expected: alle PASS.

- [ ] **Step 2: Backend-Lint**

Run: `.venv/bin/python3 -m ruff check core/src/hydrahive/runner/activity.py core/src/hydrahive/api/routes/agent_activity.py core/src/hydrahive/runner/runner.py core/src/hydrahive/tools/_sessions.py`
Expected: All checks passed.

- [ ] **Step 3: Frontend Build**

Run: `cd frontend && npx tsc -b && npx eslint .`
Expected: grün.

- [ ] **Step 4: Manueller Test (Till)**

Instanz neu starten (ohne --reload). `/pixel` an. Mit Projekt-Agent eine Delegation auslösen → der delegierte Spezialist erscheint live mit aktuellem Tool und verschwindet ~2,5 s nach Abschluss. „Chat ↔ Alle" umschalten.

---

## Offen nach diesem Feature
- App-weite Leiste (statt nur im Chat) — eigene Stufe.
- Verbindungslinien zwischen Eltern-Agent und delegierten (der Monitor zeichnet sie schon bei `interacting`; später aus dem Feed speisen).
