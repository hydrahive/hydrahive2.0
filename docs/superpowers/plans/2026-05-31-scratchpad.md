# Scratchpad Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine globale, persistente Mensch→Agent-Ideenfläche pro User — Till schreibt Markdown-Ideen (inkl. abhakbarer Punkte), der Buddy/Master liest sie und schreibt in eine getrennte Agent-Zone.

**Architecture:** Zwei physisch getrennte Markdown-Dateien pro User (`user.md`, `agent.md`) unter `data_dir/scratchpad/<user_id>/`. Backend-Service mit atomic write; zwei Core-Tools (`read_scratchpad` liest beide Zonen, `write_scratchpad` schreibt NUR `agent.md`); API für die Web-Konsole; statischer Prompt-Hinweis (cache-sicher) der nur erscheint, wenn `read_scratchpad` zugewiesen ist. Frontend-View mit eigenem Menüpunkt.

**Tech Stack:** Python 3.12 + FastAPI (Backend), pytest, React + TypeScript + Vite (Frontend), react-markdown + remark-gfm (vorhanden).

**Design-Doc:** `docs/superpowers/specs/2026-05-31-scratchpad-design.md`
**SPEC.md:** Komponente „Scratchpad" + Tools `read_scratchpad`/`write_scratchpad` (Commit `47130d77`).

---

## File Structure

| Datei | Verantwortung | Aktion |
|---|---|---|
| `core/src/hydrahive/scratchpad/__init__.py` | Package-Marker | Create |
| `core/src/hydrahive/scratchpad/service.py` | get/save/clear je Zone, atomic write, Größenlimit, combined-View | Create |
| `core/src/hydrahive/tools/read_scratchpad.py` | Tool: liest beide Zonen | Create |
| `core/src/hydrahive/tools/write_scratchpad.py` | Tool: schreibt nur Agent-Zone | Create |
| `core/src/hydrahive/tools/__init__.py` | Tool-Registry | Modify |
| `core/src/hydrahive/agents/_defaults.py` | Master-Default-Tools | Modify |
| `core/src/hydrahive/runner/system_prompt.py` | statischer Prompt-Hinweis | Modify |
| `core/src/hydrahive/api/routes/scratchpad.py` | GET/PUT/DELETE-Endpoints | Create |
| `core/src/hydrahive/api/main.py` | Router einbinden | Modify |
| `frontend/src/features/scratchpad/api.ts` | API-Client | Create |
| `frontend/src/features/scratchpad/ScratchpadPage.tsx` | View (zwei Zonen) | Create |
| `frontend/src/App.tsx` | Route | Modify |
| `frontend/src/shared/nav-config.ts` | Menüpunkt | Modify |
| `frontend/src/i18n/locales/de/nav.json` + `en/nav.json` | Label | Modify |
| `core/tests/test_scratchpad_service.py` | Service-Tests | Create |
| `core/tests/test_scratchpad_tools.py` | Tool-Tests | Create |
| `core/tests/test_scratchpad_api.py` | API-Tests | Create |
| `core/tests/test_scratchpad_prompt.py` | Prompt-Hinweis-Test | Create |

**Test-Hinweis:** Core-Tests via `cd core && python3 -m pytest tests/test_scratchpad_*.py -q`. Frontend-Check NUR via `cd frontend && ./node_modules/.bin/tsc -b` (NIE `tsc --noEmit` — toter Wächter, root-tsconfig hat `files:[]`).

---

## Task 1: Backend-Service

**Files:**
- Create: `core/src/hydrahive/scratchpad/__init__.py`
- Create: `core/src/hydrahive/scratchpad/service.py`
- Test: `core/tests/test_scratchpad_service.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_scratchpad_service.py`:
```python
from __future__ import annotations

import pytest

from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge


@pytest.fixture
def sp(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return service


def test_get_user_empty_when_absent(sp):
    assert sp.get_user("u1") == ""


def test_save_and_get_user(sp):
    sp.save_user("u1", "meine idee")
    assert sp.get_user("u1") == "meine idee"


def test_zones_are_independent(sp):
    sp.save_user("u1", "USER-TEXT")
    sp.save_agent("u1", "AGENT-TEXT")
    assert sp.get_user("u1") == "USER-TEXT"
    assert sp.get_agent("u1") == "AGENT-TEXT"


def test_save_agent_never_touches_user_zone(sp):
    """Kern-Garantie: der Agent kann Tills Text technisch nicht überschreiben."""
    sp.save_user("u1", "TILLS UNANTASTBARER TEXT")
    sp.save_agent("u1", "agent kritzelt")
    assert sp.get_user("u1") == "TILLS UNANTASTBARER TEXT"


def test_clear_agent_only(sp):
    sp.save_user("u1", "bleibt")
    sp.save_agent("u1", "geht weg")
    sp.clear_agent("u1")
    assert sp.get_agent("u1") == ""
    assert sp.get_user("u1") == "bleibt"


def test_users_isolated(sp):
    sp.save_user("u1", "A")
    sp.save_user("u2", "B")
    assert sp.get_user("u1") == "A"
    assert sp.get_user("u2") == "B"


def test_combined_contains_both_zones(sp):
    sp.save_user("u1", "IDEE-X")
    sp.save_agent("u1", "NOTIZ-Y")
    combined = sp.get_combined("u1")
    assert "IDEE-X" in combined
    assert "NOTIZ-Y" in combined


def test_too_large_rejected(sp):
    with pytest.raises(ScratchpadTooLarge):
        sp.save_user("u1", "x" * (256 * 1024 + 1))
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_service.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'hydrahive.scratchpad'`

- [ ] **Step 3: Package + Service implementieren**

`core/src/hydrahive/scratchpad/__init__.py`:
```python
"""Scratchpad — globale Mensch→Agent-Ideenfläche pro User."""
```

`core/src/hydrahive/scratchpad/service.py`:
```python
"""Scratchpad-Service: zwei physisch getrennte Zonen pro User.

user.md  — nur der Mensch (via Web-Konsole)
agent.md — nur der Agent (via write_scratchpad-Tool)

Die Trennung in zwei Dateien macht es technisch unmöglich, dass der Agent
Tills Text überschreibt. Speicher: data_dir/scratchpad/<user_id>/{user,agent}.md
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

MAX_ZONE_BYTES = 256 * 1024  # 256 KB pro Zone


class ScratchpadTooLarge(ValueError):
    """Zone-Inhalt überschreitet MAX_ZONE_BYTES."""


def _zone_path(user_id: str, zone: str) -> Path:
    return settings.data_dir / "scratchpad" / user_id / f"{zone}.md"


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("scratchpad: konnte %s nicht lesen", path)
        return ""


def _write_atomic(path: Path, content: str) -> None:
    if len(content.encode("utf-8")) > MAX_ZONE_BYTES:
        raise ScratchpadTooLarge(f"Scratchpad-Zone überschreitet {MAX_ZONE_BYTES} Bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def get_user(user_id: str) -> str:
    return _read(_zone_path(user_id, "user"))


def save_user(user_id: str, content: str) -> None:
    _write_atomic(_zone_path(user_id, "user"), content)


def get_agent(user_id: str) -> str:
    return _read(_zone_path(user_id, "agent"))


def save_agent(user_id: str, content: str) -> None:
    _write_atomic(_zone_path(user_id, "agent"), content)


def clear_agent(user_id: str) -> None:
    path = _zone_path(user_id, "agent")
    if path.exists():
        path.unlink()


def get_combined(user_id: str) -> str:
    """Beide Zonen klar beschriftet — Format das der Agent via read_scratchpad sieht."""
    user = get_user(user_id).strip() or "_(leer)_"
    agent = get_agent(user_id).strip() or "_(leer)_"
    return f"## Tills Ideen\n\n{user}\n\n## Agent-Notizen (dein Bereich)\n\n{agent}"
```

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_service.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: ruff + commit**

```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/scratchpad/ core/tests/test_scratchpad_service.py
cd /home/till/claudeneu
git add core/src/hydrahive/scratchpad/ core/tests/test_scratchpad_service.py
git commit -m "feat(scratchpad): Service mit zwei getrennten Zonen pro User"
```

---

## Task 2: Core-Tools (read + write) + Registrierung

**Files:**
- Create: `core/src/hydrahive/tools/read_scratchpad.py`
- Create: `core/src/hydrahive/tools/write_scratchpad.py`
- Modify: `core/src/hydrahive/tools/__init__.py` (Import + Registry-Liste)
- Modify: `core/src/hydrahive/agents/_defaults.py` (`"master"`-Liste)
- Test: `core/tests/test_scratchpad_tools.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_scratchpad_tools.py`:
```python
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.scratchpad import service
from hydrahive.tools import read_scratchpad, write_scratchpad
from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1", workspace=Path(tmp_path)
    )


def test_read_returns_both_zones(ctx):
    service.save_user("u1", "IDEE-A")
    service.save_agent("u1", "NOTIZ-B")
    result = asyncio.run(read_scratchpad.TOOL.execute({}, ctx))
    assert result.success
    assert "IDEE-A" in result.output
    assert "NOTIZ-B" in result.output


def test_write_only_touches_agent_zone(ctx):
    service.save_user("u1", "TILLS TEXT")
    result = asyncio.run(write_scratchpad.TOOL.execute({"content": "agent neu"}, ctx))
    assert result.success
    assert service.get_agent("u1") == "agent neu"
    assert service.get_user("u1") == "TILLS TEXT"  # unangetastet


def test_write_rejects_non_string(ctx):
    result = asyncio.run(write_scratchpad.TOOL.execute({"content": 123}, ctx))
    assert not result.success


def test_tools_registered():
    from hydrahive.tools import REGISTRY
    assert "read_scratchpad" in REGISTRY
    assert "write_scratchpad" in REGISTRY


def test_master_has_scratchpad_tools():
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    assert "read_scratchpad" in DEFAULT_TOOLS["master"]
    assert "write_scratchpad" in DEFAULT_TOOLS["master"]
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_tools.py -q`
Expected: FAIL mit `ImportError: cannot import name 'read_scratchpad'`

- [ ] **Step 3: Tools implementieren**

`core/src/hydrahive/tools/read_scratchpad.py`:
```python
from __future__ import annotations

from hydrahive.scratchpad import service
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest das Scratchpad des Users: Tills handgeschriebene Ideen plus deine "
    "eigenen Agent-Notizen. Nutze es, wenn die Aufgabe auf notierte Ideen Bezug nimmt."
)

_SCHEMA = {"type": "object", "properties": {}, "required": []}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(service.get_combined(ctx.user_id))


TOOL = Tool(
    name="read_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
)
```

`core/src/hydrahive/tools/write_scratchpad.py`:
```python
from __future__ import annotations

from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Schreibt in DEINE Agent-Notiz-Zone des Scratchpads (ersetzt sie komplett). "
    "Tills eigener Bereich ist tabu und kann hierüber nicht verändert werden. "
    "Lies vorher mit read_scratchpad, damit du deine bestehenden Notizen nicht verlierst."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "Vollständiger neuer Inhalt deiner Agent-Zone (Markdown).",
        },
    },
    "required": ["content"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    content = args.get("content")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")
    try:
        service.save_agent(ctx.user_id, content)
    except ScratchpadTooLarge as e:
        return ToolResult.fail(str(e))
    return ToolResult.ok("Agent-Notizen gespeichert.")


TOOL = Tool(
    name="write_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
)
```

- [ ] **Step 4: In tools/__init__.py registrieren**

In `core/src/hydrahive/tools/__init__.py` den Import-Block (alphabetisch bei `r`/`w`) ergänzen — `read_scratchpad` neben `read_memory`, `write_scratchpad` neben `write_memory`:
```python
    read_memory,
    read_scratchpad,
    search_memory,
    send_mail,
    shell,
    todo,
    web_browser,
    web_search,
    webmin_call,
    webmin_status,
    write_memory,
    write_scratchpad,
```
Und in `_build_registry()` die `tools`-Liste ergänzen (nach `load_skill.TOOL`):
```python
        load_skill.TOOL,
        read_scratchpad.TOOL,
        write_scratchpad.TOOL,
```

- [ ] **Step 5: In agents/_defaults.py der master-Liste hinzufügen**

In `core/src/hydrahive/agents/_defaults.py`, `_BASE_TOOLS["master"]` — nach `"list_skills", "load_skill",`:
```python
        "list_skills", "load_skill",
        "read_scratchpad", "write_scratchpad",
```

- [ ] **Step 6: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_tools.py -q`
Expected: PASS (5 passed)

- [ ] **Step 7: ruff + commit**

```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/tools/ core/tests/test_scratchpad_tools.py
cd /home/till/claudeneu
git add core/src/hydrahive/tools/ core/src/hydrahive/agents/_defaults.py core/tests/test_scratchpad_tools.py
git commit -m "feat(scratchpad): read_scratchpad + write_scratchpad Tools, Master-Default"
```

---

## Task 3: API-Route

**Files:**
- Create: `core/src/hydrahive/api/routes/scratchpad.py`
- Modify: `core/src/hydrahive/api/main.py`
- Test: `core/tests/test_scratchpad_api.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_scratchpad_api.py`:
```python
from __future__ import annotations


def test_get_empty_scratchpad(client, auth_headers):
    r = client.get("/api/scratchpad", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"user_content": "", "agent_content": ""}


def test_put_then_get_roundtrip(client, auth_headers):
    put = client.put("/api/scratchpad", json={"content": "meine idee"}, headers=auth_headers)
    assert put.status_code == 200
    assert put.json() == {"saved": True}
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["user_content"] == "meine idee"


def test_put_only_sets_user_zone(client, auth_headers):
    client.put("/api/scratchpad", json={"content": "USER"}, headers=auth_headers)
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["user_content"] == "USER"
    assert got.json()["agent_content"] == ""  # PUT berührt agent-Zone nicht


def test_delete_agent_zone(client, auth_headers):
    # Agent-Zone direkt über den Service befüllen, dann via API leeren
    from hydrahive.scratchpad import service
    r = client.get("/api/auth/me", headers=auth_headers)
    user = r.json()["username"]
    service.save_agent(user, "agent notiz")
    deleted = client.delete("/api/scratchpad/agent", headers=auth_headers)
    assert deleted.status_code == 200
    got = client.get("/api/scratchpad", headers=auth_headers)
    assert got.json()["agent_content"] == ""


def test_requires_auth(client):
    assert client.get("/api/scratchpad").status_code == 401
```

> Hinweis: Falls `/api/auth/me` nicht existiert oder ein anderes Feld liefert, im Test stattdessen `"testuser"` direkt verwenden (die conftest legt testuser an, und `require_auth` liefert genau diesen Usernamen). Prüfe die vorhandene auth-Route vor dem Lauf.

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_api.py -q`
Expected: FAIL (404 auf `/api/scratchpad`, Router noch nicht eingebunden)

- [ ] **Step 3: Route implementieren**

`core/src/hydrahive/api/routes/scratchpad.py`:
```python
"""Scratchpad-Endpoints: Mensch-Zone editierbar, Agent-Zone read-only + leerbar."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge

router = APIRouter(prefix="/api/scratchpad", tags=["scratchpad"])


class ScratchpadBody(BaseModel):
    content: str = Field(default="", max_length=262144)


@router.get("")
def get_scratchpad(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    return {"user_content": service.get_user(user), "agent_content": service.get_agent(user)}


@router.put("")
def put_scratchpad(
    body: ScratchpadBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    try:
        service.save_user(user, body.content)
    except ScratchpadTooLarge as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "scratchpad_too_large", message=str(e))
    return {"saved": True}


@router.delete("/agent")
def clear_agent_zone(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    service.clear_agent(user)
    return {"cleared": True}
```

- [ ] **Step 4: Router in main.py einbinden**

In `core/src/hydrahive/api/main.py` bei den Imports (alphabetisch im `routes`-Block):
```python
from hydrahive.api.routes.scratchpad import router as scratchpad_router
```
Und bei den `app.include_router(...)`-Aufrufen (neben den anderen):
```python
app.include_router(scratchpad_router)
```

- [ ] **Step 5: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_api.py -q`
Expected: PASS (5 passed). Falls `test_delete_agent_zone` an `/api/auth/me` scheitert: Username-Beschaffung wie im Step-1-Hinweis auf `"testuser"` umstellen.

- [ ] **Step 6: ruff + commit**

```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/api/routes/scratchpad.py core/tests/test_scratchpad_api.py
cd /home/till/claudeneu
git add core/src/hydrahive/api/routes/scratchpad.py core/src/hydrahive/api/main.py core/tests/test_scratchpad_api.py
git commit -m "feat(scratchpad): API — GET beide Zonen, PUT user, DELETE agent"
```

---

## Task 4: Statischer Prompt-Hinweis (cache-sicher)

**Files:**
- Modify: `core/src/hydrahive/runner/system_prompt.py`
- Test: `core/tests/test_scratchpad_prompt.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_scratchpad_prompt.py`:
```python
from __future__ import annotations

from pathlib import Path

from hydrahive.runner.system_prompt import compose


def _compose(allowed):
    stable, _volatile, _summary = compose(
        "BASE",
        extra_system=None,
        workspace=Path("/tmp/ws"),
        summary=None,
        skills=None,
        longterm_memory=False,
        tool_schemas=[],
        allowed_tools=allowed,
    )
    return stable


def test_hint_present_when_tool_allowed():
    stable = _compose(["read_scratchpad", "write_scratchpad"])
    assert "Scratchpad" in stable
    assert "read_scratchpad" in stable


def test_hint_absent_without_tool():
    stable = _compose(["file_read"])
    assert "Scratchpad" not in stable
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_prompt.py -q`
Expected: FAIL (`test_hint_present_when_tool_allowed` — "Scratchpad" nicht im stable)

- [ ] **Step 3: Hinweis implementieren**

In `core/src/hydrahive/runner/system_prompt.py` nach der `_LONGTERM_MEMORY_HINT`-Konstante eine neue Konstante ergänzen:
```python
_SCRATCHPAD_HINT = (
    "\n\nScratchpad: Till hinterlegt hier Ideen und Notizen. Lies sie mit "
    "`read_scratchpad`, wenn die Aufgabe darauf Bezug nimmt. Eigene Notizen "
    "schreibst du mit `write_scratchpad` — nur in deinen Bereich; Tills Bereich ist tabu."
)
```
In `compose()` nach dem `if longterm_memory:`-Block und vor `if recall_cards:`:
```python
    if longterm_memory:
        stable = _inject_longterm_memory(stable, tool_schemas, allowed_tools)
    if "read_scratchpad" in allowed_tools:
        stable += _SCRATCHPAD_HINT
    if recall_cards:
        stable += render_cards_block(recall_cards)
```

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_scratchpad_prompt.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Volle Backend-Suite + ruff + commit**

```bash
cd core && python3 -m pytest tests/test_scratchpad_*.py -q
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/runner/system_prompt.py core/tests/test_scratchpad_prompt.py
cd /home/till/claudeneu
git add core/src/hydrahive/runner/system_prompt.py core/tests/test_scratchpad_prompt.py
git commit -m "feat(scratchpad): statischer Prompt-Hinweis wenn read_scratchpad zugewiesen"
```

---

## Task 5: Frontend — View + Menüpunkt

**Files:**
- Create: `frontend/src/features/scratchpad/api.ts`
- Create: `frontend/src/features/scratchpad/ScratchpadPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/shared/nav-config.ts`
- Modify: `frontend/src/i18n/locales/de/nav.json`, `frontend/src/i18n/locales/en/nav.json`

> Kein Unit-Test im Frontend (visuelles Feature, Till verifiziert im Browser). Exit-Gate: `tsc -b` grün.

- [ ] **Step 1: API-Client**

`frontend/src/features/scratchpad/api.ts`:
```typescript
import { api } from "@/shared/api-client"

export interface ScratchpadData {
  user_content: string
  agent_content: string
}

export const scratchpadApi = {
  get: () => api.get<ScratchpadData>("/scratchpad"),
  saveUser: (content: string) => api.put<{ saved: boolean }>("/scratchpad", { content }),
  clearAgent: () => api.delete<{ cleared: boolean }>("/scratchpad/agent"),
}
```

- [ ] **Step 2: View**

`frontend/src/features/scratchpad/ScratchpadPage.tsx`:
```tsx
import { useEffect, useRef, useState } from "react"
import { Markdown } from "@/features/chat/Markdown"
import { scratchpadApi } from "./api"

export function ScratchpadPage() {
  const [userText, setUserText] = useState("")
  const [agentText, setAgentText] = useState("")
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(true)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    scratchpadApi.get()
      .then((d) => { setUserText(d.user_content); setAgentText(d.agent_content) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const onChange = (v: string) => {
    setUserText(v)
    setSaved(false)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      scratchpadApi.saveUser(v).then(() => setSaved(true)).catch(() => {})
    }, 800)
  }

  const clearAgent = () => {
    if (!confirm("Agent-Notizen wirklich leeren?")) return
    scratchpadApi.clearAgent().then(() => setAgentText("")).catch(() => {})
  }

  if (loading) {
    return <div className="h-48 m-6 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-zinc-100">Scratchpad</h1>
        <span className="text-xs text-zinc-600">{saved ? "gespeichert" : "speichert…"}</span>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-zinc-300">Meine Ideen</h2>
        <div className="grid grid-cols-2 gap-4">
          <textarea
            value={userText}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Ideen, Notizen, Aufgaben (Markdown, `- [ ]` für Checkboxen)…"
            className="min-h-[24rem] rounded-xl border border-white/[8%] bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 font-mono resize-y"
          />
          <div className="min-h-[24rem] rounded-xl border border-white/[6%] bg-zinc-900/40 px-4 py-3 overflow-auto">
            <Markdown text={userText || "_(leer)_"} />
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-zinc-300">Agent-Notizen</h2>
          <span className="text-xs text-zinc-600">(nur der Agent schreibt hier)</span>
          <button
            onClick={clearAgent}
            className="ml-auto text-xs text-zinc-500 hover:text-red-400 px-2 py-1 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
          >
            Leeren
          </button>
        </div>
        <div className="rounded-xl border border-violet-500/15 bg-violet-500/[4%] px-4 py-3">
          <Markdown text={agentText || "_(noch keine Agent-Notizen)_"} />
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: Route in App.tsx**

In `frontend/src/App.tsx` einen Import bei den anderen Page-Imports ergänzen:
```tsx
import { ScratchpadPage } from "@/features/scratchpad/ScratchpadPage"
```
Und eine Route bei den anderen (z.B. nach der `werkstatt`-Route):
```tsx
          <Route path="scratchpad" element={<ScratchpadPage />} />
```

- [ ] **Step 4: Menüpunkt in nav-config.ts**

In `frontend/src/shared/nav-config.ts` den lucide-Import um `StickyNote` ergänzen (im bestehenden Import-Block) und in `NAV_ITEMS` in der Gruppe „working" einen Eintrag ergänzen (nach der `buddy`-Zeile):
```tsx
  { path: "/scratchpad", icon: StickyNote, labelKey: "scratchpad", group: "working" },
```

- [ ] **Step 5: i18n-Labels**

In `frontend/src/i18n/locales/de/nav.json` im `items`-Objekt ergänzen:
```json
    "scratchpad": "Scratchpad",
```
In `frontend/src/i18n/locales/en/nav.json` im `items`-Objekt ergänzen:
```json
    "scratchpad": "Scratchpad",
```

- [ ] **Step 6: tsc -b grün**

Run: `cd frontend && ./node_modules/.bin/tsc -b`
Expected: Exit 0, keine Ausgabe.

- [ ] **Step 7: commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/scratchpad/ frontend/src/App.tsx frontend/src/shared/nav-config.ts frontend/src/i18n/locales/de/nav.json frontend/src/i18n/locales/en/nav.json
git commit -m "feat(scratchpad): Frontend-View + Menüpunkt (zwei Zonen, Auto-Save)"
```

---

## Task 6: Verify (Till, im Browser)

> Nach dem Update auf dem Server (zieht `main`):

- [ ] Menüpunkt „Scratchpad" erscheint in der Gruppe „Arbeiten"
- [ ] Text in „Meine Ideen" tippen → Preview rendert Markdown + `- [ ]` als Checkboxen; „gespeichert" erscheint nach kurzer Pause; Reload behält den Text
- [ ] Buddy/Master im Chat fragen, was im Scratchpad steht → er ruft `read_scratchpad` und gibt den Inhalt wieder
- [ ] Buddy bitten, eine Notiz zu hinterlassen → erscheint im „Agent-Notizen"-Bereich, „Meine Ideen" bleibt unverändert
- [ ] „Agent-Notizen leeren" funktioniert, Mensch-Zone bleibt erhalten

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Coverage:** global pro User (Task 1 `_zone_path` user_id) ✓; persistent + abhakbar (Task 1 Dateien + Task 5 remark-gfm Checkboxen) ✓; Markdown+Mermaid (Task 5 Markdown.tsx — Mermaid v1 als Code-Block, kein Render, = Nicht-Ziel) ✓; Hybrid-Lesemodus (Task 4 statischer Hinweis + Task 2 Tools) ✓; getrennte Zonen (Task 1 zwei Dateien, Task 2 `test_write_only_touches_agent_zone`) ✓; eigener Menüpunkt (Task 5) ✓; cache-sicher (Task 4 statischer Text in stable, Inhalt nur via Tool-Result) ✓.

**Platzhalter-Scan:** keine TBD/TODO; jeder Code-Step enthält vollständigen Code. Einzige Unsicherheit (`/api/auth/me` für Username im API-Test) ist mit konkretem Fallback (`"testuser"`) versehen.

**Typ-Konsistenz:** `ScratchpadTooLarge`, `get_user/save_user/get_agent/save_agent/clear_agent/get_combined`, `ToolContext.user_id`, `scratchpadApi.get/saveUser/clearAgent`, `ScratchpadData{user_content,agent_content}` — über alle Tasks identisch verwendet.
