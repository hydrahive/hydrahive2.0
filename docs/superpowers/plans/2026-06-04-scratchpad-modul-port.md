# Scratchpad → Modul (+ Modul-Agent-Tool-Vertrag) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scratchpad vollständig aus dem Core in ein Opt-in-Modul auslagern und dabei den generischen Vertrag „Module bringen Agent-Tools + Prompt-Hinweise + Default-Tool-Teilnahme mit" etablieren.

**Architecture:** Drei Phasen. Phase 1 erweitert den Modul-Vertrag im Core (generisch, TDD). Phase 2 baut das Scratchpad-Modul im Hub-Repo. Phase 3 entfernt Scratchpad aus dem Core. Zwischen den Phasen bleibt der Core jederzeit grün.

**Tech Stack:** Python 3.12 / FastAPI / pytest (Core), React+TS+Vite (Frontend), eigenes Modulsystem (`hydrahive.modules`), Hub-Repo `git@github.com:hydrahive/hydrahive2-modules.git`.

**Spec:** `docs/superpowers/specs/2026-06-04-scratchpad-modul-port-design.md`

**Zwei Repos:**
- Core: `/home/till/claudeneu` (Phase 1 + 3)
- Hub: `/home/till/hydrahive2-modules` (Phase 2)

**Test-Runner:** `/home/till/claudeneu/.venv/bin/pytest` (aus `core/` ausführen). Frontend-Build aus `frontend/`: `npm run build`.

---

## File Structure

**Phase 1 (Core, geändert):**
- `core/src/hydrahive/tools/base.py` — `Tool.prompt_hint: str = ""`
- `core/src/hydrahive/runner/system_prompt.py` — generische Hint-Schleife statt Scratchpad-Spezialfall
- `core/src/hydrahive/tools/read_scratchpad.py` — `prompt_hint` auf dem TOOL gesetzt (Hint zieht hierher, bis Phase 3)
- `core/src/hydrahive/modules/context.py` — `register_tool` + `self.tools`
- `core/src/hydrahive/tools/__init__.py` — `register_module_tools()` + `_MODULE_TOOL_NAMES`
- `core/src/hydrahive/modules/manifest.py` — `default_agent_tools: bool`
- `core/src/hydrahive/agents/_defaults.py` — `_module_default_tool_names()` + `_filtered()` erweitert
- `core/src/hydrahive/api/lifespan.py` — `register_module_tools(...)` nach `load_all()`
- Neue Tests: `core/tests/test_tool_prompt_hint.py`, `test_module_context_tools.py`, `test_register_module_tools.py`, `test_manifest_default_tools.py`, `test_module_default_tools.py`

**Phase 2 (Hub-Repo, neu):**
- `scratchpad/manifest.json`
- `scratchpad/backend/{__init__,service,routes,tools}.py`
- `scratchpad/frontend/{index.tsx,ScratchpadPage.tsx,api.ts}`
- `hub.json` (Eintrag ergänzt)

**Phase 3 (Core, gelöscht):** siehe Tasks 10–11.

---

# PHASE 1 — Modul-Agent-Tool-Vertrag (Core, generisch)

### Task 1: `Tool.prompt_hint` + generischer System-Prompt-Hinweis

**Files:**
- Modify: `core/src/hydrahive/tools/base.py`
- Modify: `core/src/hydrahive/runner/system_prompt.py`
- Modify: `core/src/hydrahive/tools/read_scratchpad.py`
- Create: `core/tests/test_tool_prompt_hint.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_tool_prompt_hint.py`:
```python
from __future__ import annotations

from pathlib import Path

from hydrahive.runner.system_prompt import compose
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok("x")


def _compose(allowed):
    stable, _v, _s = compose(
        "BASE", extra_system=None, workspace=Path("/tmp/ws"), summary=None,
        skills=None, longterm_memory=False, tool_schemas=[], allowed_tools=allowed,
    )
    return stable


def test_prompt_hint_injected_when_tool_allowed(monkeypatch):
    fake = Tool(name="faketool", description="d", schema={}, execute=_noop,
                prompt_hint="\n\nFAKE-HINT-XYZ")
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool", fake)
    assert "FAKE-HINT-XYZ" in _compose(["faketool"])


def test_prompt_hint_absent_when_tool_not_allowed(monkeypatch):
    fake = Tool(name="faketool", description="d", schema={}, execute=_noop,
                prompt_hint="\n\nFAKE-HINT-XYZ")
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool", fake)
    assert "FAKE-HINT-XYZ" not in _compose(["file_read"])


def test_tool_without_hint_adds_nothing(monkeypatch):
    fake = Tool(name="faketool2", description="d", schema={}, execute=_noop)
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool2", fake)
    out = _compose(["faketool2"])
    assert "FAKE-HINT" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_tool_prompt_hint.py -q`
Expected: FAIL — `Tool.__init__() got an unexpected keyword argument 'prompt_hint'`.

- [ ] **Step 3: Add the field**

`core/src/hydrahive/tools/base.py` — erweitere die `Tool`-Dataclass:
```python
@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    execute: ExecuteFn
    category: str = "other"
    prompt_hint: str = ""
```

- [ ] **Step 4: Make the system prompt generic**

`core/src/hydrahive/runner/system_prompt.py` — in `compose()` die Zeilen
```python
    if "read_scratchpad" in allowed_tools:
        stable += _SCRATCHPAD_HINT
```
ersetzen durch:
```python
    stable += _tool_prompt_hints(allowed_tools)
```
Die Konstante `_SCRATCHPAD_HINT` (Block bei ~Zeile 98–102) löschen und folgenden Helfer ergänzen (nahe den anderen privaten Buildern):
```python
def _tool_prompt_hints(allowed_tools: list[str]) -> str:
    """Hängt den prompt_hint jedes erlaubten Tools an, das einen hat.
    Lazy-Import von REGISTRY vermeidet Import-Zyklen (runner ↔ tools)."""
    from hydrahive.tools import REGISTRY
    out = ""
    for name in allowed_tools:
        tool = REGISTRY.get(name)
        if tool and tool.prompt_hint:
            out += tool.prompt_hint
    return out
```

- [ ] **Step 5: Move the scratchpad hint onto its tool (hält bestehende Tests grün)**

`core/src/hydrahive/tools/read_scratchpad.py` — Hint-Text als Konstante + auf dem TOOL setzen:
```python
_PROMPT_HINT = (
    "\n\nScratchpad: Till hinterlegt hier Ideen und Notizen. Lies sie mit "
    "`read_scratchpad`, wenn die Aufgabe darauf Bezug nimmt. Eigene Notizen "
    "schreibst du mit `write_scratchpad` — nur in deinen Bereich; Tills Bereich ist tabu."
)

TOOL = Tool(
    name="read_scratchpad",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="scratchpad",
    prompt_hint=_PROMPT_HINT,
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `../.venv/bin/pytest tests/test_tool_prompt_hint.py tests/test_scratchpad_prompt.py -q`
Expected: PASS (neuer generischer Test + bestehender Scratchpad-Prompt-Test, der jetzt über den generischen Pfad grün bleibt).

- [ ] **Step 7: Commit**

```bash
cd /home/till/claudeneu
git add core/src/hydrahive/tools/base.py core/src/hydrahive/runner/system_prompt.py core/src/hydrahive/tools/read_scratchpad.py core/tests/test_tool_prompt_hint.py
git commit -m "feat(modules): Tool.prompt_hint + generischer System-Prompt-Hinweis"
```

---

### Task 2: `ModuleContext.register_tool`

**Files:**
- Modify: `core/src/hydrahive/modules/context.py`
- Create: `core/tests/test_module_context_tools.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_module_context_tools.py`:
```python
from __future__ import annotations

from hydrahive.modules.context import ModuleContext
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def test_register_tool_collects():
    ctx = ModuleContext("demo")
    t = Tool(name="demo_tool", description="d", schema={}, execute=_noop)
    ctx.register_tool(t)
    assert ctx.tools == [t]


def test_tools_default_empty():
    assert ModuleContext("demo").tools == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_module_context_tools.py -q`
Expected: FAIL — `AttributeError: 'ModuleContext' object has no attribute 'tools'`.

- [ ] **Step 3: Implement**

`core/src/hydrahive/modules/context.py` — Tool-Annotation via TYPE_CHECKING (kein Laufzeit-Import von `tools`, vermeidet das schwere `tools/__init__` beim frühen Import):
```python
from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import APIRouter

if TYPE_CHECKING:
    from hydrahive.tools.base import Tool


class ModuleContext:
    """Was ein Modul beim register() registrieren kann."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.routers: list[APIRouter] = []
        self.tools: list["Tool"] = []
        self.migrations_rel: str | None = None
        self.service_rel: str | None = None

    def register_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def register_tool(self, tool: "Tool") -> None:
        self.tools.append(tool)

    def register_migrations(self, rel_dir: str) -> None:
        self.migrations_rel = rel_dir

    def register_service(self, rel_dir: str) -> None:
        self.service_rel = rel_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/pytest tests/test_module_context_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/modules/context.py core/tests/test_module_context_tools.py
git commit -m "feat(modules): ModuleContext.register_tool"
```

---

### Task 3: `tools.register_module_tools` (idempotenter Merge in REGISTRY)

**Files:**
- Modify: `core/src/hydrahive/tools/__init__.py`
- Create: `core/tests/test_register_module_tools.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_register_module_tools.py`:
```python
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def _tool(name):
    return Tool(name=name, description="d", schema={}, execute=_noop)


def test_module_tool_lands_in_registry():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    try:
        assert "mod_a" in tools.REGISTRY
    finally:
        tools.register_module_tools([])  # cleanup


def test_reregister_replaces_without_duplicates():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    tools.register_module_tools([_tool("mod_b")])  # neuer Satz
    try:
        assert "mod_b" in tools.REGISTRY
        assert "mod_a" not in tools.REGISTRY  # alter Modul-Tool entfernt
    finally:
        tools.register_module_tools([])


def test_empty_clears_module_tools():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    tools.register_module_tools([])
    assert "mod_a" not in tools.REGISTRY


def test_core_tools_untouched():
    from hydrahive import tools
    tools.register_module_tools([_tool("mod_a")])
    try:
        assert "shell_exec" in tools.REGISTRY  # Core-Tool bleibt
    finally:
        tools.register_module_tools([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_register_module_tools.py -q`
Expected: FAIL — `AttributeError: module 'hydrahive.tools' has no attribute 'register_module_tools'`.

- [ ] **Step 3: Implement**

`core/src/hydrahive/tools/__init__.py` — nach `REGISTRY = _build_registry()` ergänzen:
```python
_MODULE_TOOL_NAMES: set[str] = set()


def register_module_tools(tools: list[Tool]) -> None:
    """Merged Modul-Tools idempotent in REGISTRY. Vorher gemergte Modul-Tools
    werden zuerst entfernt — load_all ist idempotent, ein erneuter Aufruf darf
    nicht duplizieren oder Leichen hinterlassen. REGISTRY bleibt die einzige
    Tool-Quelle, damit get_tool/schemas_for/_defaults unverändert funktionieren."""
    for name in _MODULE_TOOL_NAMES:
        REGISTRY.pop(name, None)
    _MODULE_TOOL_NAMES.clear()
    for tool in tools:
        REGISTRY[tool.name] = tool
        _MODULE_TOOL_NAMES.add(tool.name)
```
Und `"register_module_tools"` zum `__all__` hinzufügen.

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/pytest tests/test_register_module_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/__init__.py core/tests/test_register_module_tools.py
git commit -m "feat(modules): tools.register_module_tools (idempotenter Registry-Merge)"
```

---

### Task 4: `manifest.default_agent_tools`

**Files:**
- Modify: `core/src/hydrahive/modules/manifest.py`
- Create: `core/tests/test_manifest_default_tools.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_manifest_default_tools.py`:
```python
from __future__ import annotations

import json

from hydrahive.modules.manifest import ModuleManifest


def _write(tmp_path, extra):
    d = {"id": "m", "name": "M", "version": "1.0.0", **extra}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(d))
    return p


def test_flag_true(tmp_path):
    m = ModuleManifest.load(_write(tmp_path, {"default_agent_tools": True}))
    assert m.default_agent_tools is True


def test_flag_defaults_false(tmp_path):
    m = ModuleManifest.load(_write(tmp_path, {}))
    assert m.default_agent_tools is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_manifest_default_tools.py -q`
Expected: FAIL — `AttributeError: 'ModuleManifest' object has no attribute 'default_agent_tools'`.

- [ ] **Step 3: Implement**

`core/src/hydrahive/modules/manifest.py` — Feld + Parsing:
```python
@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    icon: str = "Boxes"
    nav_group: str = "working"
    permissions: tuple[str, ...] = ()
    has_service: bool = False
    default_agent_tools: bool = False
    min_core_version: str = "2.0.0"
```
Und im `return cls(...)` ergänzen:
```python
            default_agent_tools=bool(d.get("default_agent_tools", False)),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/pytest tests/test_manifest_default_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/modules/manifest.py core/tests/test_manifest_default_tools.py
git commit -m "feat(modules): manifest default_agent_tools-Flag"
```

---

### Task 5: Default-Tools modul-bewusst (`_defaults`)

**Files:**
- Modify: `core/src/hydrahive/agents/_defaults.py`
- Create: `core/tests/test_module_default_tools.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_module_default_tools.py`:
```python
from __future__ import annotations

from pathlib import Path

from hydrahive.modules.context import ModuleContext
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import REGISTRY as MODREG, LoadedModule
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok()


def _install_fake_module(monkeypatch, *, flag: bool, tool_name: str):
    from hydrahive import tools
    tool = Tool(name=tool_name, description="d", schema={}, execute=_noop)
    ctx = ModuleContext("fakemod")
    ctx.register_tool(tool)
    manifest = ModuleManifest(id="fakemod", name="F", version="1.0.0",
                              default_agent_tools=flag)
    lm = LoadedModule(name="fakemod", manifest=manifest, path=Path("/x"),
                      ctx=ctx, loaded=True)
    monkeypatch.setitem(MODREG, "fakemod", lm)
    tools.register_module_tools([tool])
    monkeypatch.setattr(tools, "_MODULE_TOOL_NAMES", set(), raising=False)  # reset-Schutz
    return tool


def test_flagged_module_tool_in_master_defaults(monkeypatch):
    from hydrahive import tools
    _install_fake_module(monkeypatch, flag=True, tool_name="fakemod_tool")
    try:
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        assert "fakemod_tool" in DEFAULT_TOOLS["master"]
    finally:
        tools.register_module_tools([])


def test_unflagged_module_tool_not_in_defaults(monkeypatch):
    from hydrahive import tools
    _install_fake_module(monkeypatch, flag=False, tool_name="fakemod_tool2")
    try:
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        assert "fakemod_tool2" not in DEFAULT_TOOLS["master"]
    finally:
        tools.register_module_tools([])


def test_unregistered_module_tool_filtered(monkeypatch):
    # Flag gesetzt, aber Tool NICHT in tools.REGISTRY → muss rausgefiltert werden.
    from hydrahive import tools
    ctx = ModuleContext("ghost")
    ctx.register_tool(Tool(name="ghost_tool", description="d", schema={}, execute=_noop))
    manifest = ModuleManifest(id="ghost", name="G", version="1.0.0", default_agent_tools=True)
    monkeypatch.setitem(MODREG, "ghost",
                        LoadedModule(name="ghost", manifest=manifest, path=Path("/x"),
                                     ctx=ctx, loaded=True))
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    assert "ghost_tool" not in DEFAULT_TOOLS["master"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_module_default_tools.py -q`
Expected: FAIL — flagged tool nicht in master defaults.

- [ ] **Step 3: Implement**

`core/src/hydrahive/agents/_defaults.py` — `_filtered()` ersetzen + Helfer ergänzen:
```python
def _module_default_tool_names() -> list[str]:
    """Tool-Namen aus geladenen Modulen mit default_agent_tools=true."""
    try:
        from hydrahive.modules.registry import REGISTRY as MODULES
    except Exception:
        return []
    names: list[str] = []
    for m in MODULES.values():
        if m.loaded and m.ctx and m.manifest and m.manifest.default_agent_tools:
            names.extend(t.name for t in m.ctx.tools)
    return names


def _filtered() -> dict[str, list[str]]:
    """Filtert nicht-registrierte Tools raus; Master bekommt zusätzlich die
    Default-Tools installierter Module (Manifest-Flag)."""
    from hydrahive.tools import REGISTRY  # lazy um Zyklen zu vermeiden
    module_master = _module_default_tool_names()
    result: dict[str, list[str]] = {}
    for agent_type, tools in _BASE_TOOLS.items():
        names = list(tools) + (module_master if agent_type == "master" else [])
        result[agent_type] = [t for t in names if t in REGISTRY]
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/pytest tests/test_module_default_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/agents/_defaults.py core/tests/test_module_default_tools.py
git commit -m "feat(modules): Master-Default-Tools um Modul-Tools (Manifest-Flag) erweitern"
```

---

### Task 6: Lifespan-Verdrahtung (Modul-Tools nach load_all registrieren)

**Files:**
- Modify: `core/src/hydrahive/api/lifespan.py:120-123`
- Create: `core/tests/test_lifespan_module_tools.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_lifespan_module_tools.py` (nutzt den echten Loader mit einem Fake-Modul, das ein Tool registriert):
```python
from __future__ import annotations

import json


def test_module_tool_registered_after_load(mod_env):
    md = mod_env / "modules" / "tmod"
    (md / "backend").mkdir(parents=True)
    (md / "manifest.json").write_text(json.dumps(
        {"id": "tmod", "name": "T", "version": "1.0.0", "default_agent_tools": True}))
    (md / "backend" / "__init__.py").write_text(
        "from hydrahive.tools.base import Tool, ToolResult\n"
        "async def _x(a, c):\n"
        "    return ToolResult.ok('ok')\n"
        "TOOL = Tool(name='tmod_tool', description='d', schema={}, execute=_x,\n"
        "            prompt_hint='\\n\\nTMOD-HINT')\n"
        "def register(ctx):\n"
        "    ctx.register_tool(TOOL)\n"
    )
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY as MODREG
    from hydrahive import tools
    load_all()
    collected = [t for m in MODREG.values() if m.loaded and m.ctx for t in m.ctx.tools]
    tools.register_module_tools(collected)
    try:
        assert "tmod_tool" in tools.REGISTRY
    finally:
        tools.register_module_tools([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/pytest tests/test_lifespan_module_tools.py -q`
Expected: FAIL zunächst NICHT durch fehlenden Code (register_module_tools existiert seit Task 3), sondern der Test ist die Integrationsabsicherung. Falls er schon grün ist: gut — er fixiert das Verhalten. Der eigentliche Lifespan-Edit folgt in Step 3 und wird durch den vollen Suite-Lauf abgesichert (kein isolierter Lifespan-Unit-Test sinnvoll).

> Hinweis: Dieser Test prüft die Sammel-/Merge-Logik, die der Lifespan ausführt. Der Lifespan selbst wird über Step 3 + Suite verifiziert.

- [ ] **Step 3: Verdrahte den Lifespan**

`core/src/hydrahive/api/lifespan.py` — den Block bei Zeile 120–123:
```python
    from hydrahive import modules as module_system
    module_system.load_all()
    from hydrahive.api.main import mount_module_routers
    mount_module_routers(app)
```
ergänzen um:
```python
    from hydrahive.modules.registry import REGISTRY as _module_registry
    from hydrahive.tools import register_module_tools
    register_module_tools([
        t for m in _module_registry.values()
        if m.loaded and m.ctx for t in m.ctx.tools
    ])
```

- [ ] **Step 4: Run tests**

Run: `../.venv/bin/pytest tests/test_lifespan_module_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/api/lifespan.py core/tests/test_lifespan_module_tools.py
git commit -m "feat(modules): Modul-Tools im Lifespan nach load_all registrieren"
```

---

### Task 7: Phase-1-Abschluss — volle Suite grün

- [ ] **Step 1: Run the full backend suite**

Run: `cd /home/till/claudeneu/core && ../.venv/bin/pytest -q`
Expected: alle grün (bestehende Scratchpad-Tests laufen weiter über den generischen Hint-Pfad; neue Vertrags-Tests grün). Falls rot: Ursache beheben, bevor Phase 2 beginnt.

- [ ] **Step 2: (kein Commit nötig — reiner Verifikationslauf)**

---

# PHASE 2 — Scratchpad-Modul (Hub-Repo `/home/till/hydrahive2-modules`)

> Alle Phase-2-Pfade sind relativ zu `/home/till/hydrahive2-modules`.

### Task 8: Modul-Backend (manifest + service + routes + tools + register)

**Files:**
- Create: `scratchpad/manifest.json`
- Create: `scratchpad/backend/service.py`
- Create: `scratchpad/backend/routes.py`
- Create: `scratchpad/backend/tools.py`
- Create: `scratchpad/backend/__init__.py`

- [ ] **Step 1: manifest.json**
```json
{
  "id": "scratchpad",
  "name": "Scratchpad",
  "version": "1.0.0",
  "icon": "StickyNote",
  "nav_group": "working",
  "permissions": [],
  "has_service": false,
  "default_agent_tools": true,
  "min_core_version": "2.0.0"
}
```

- [ ] **Step 2: backend/service.py** (1:1 aus `core/src/hydrahive/scratchpad/service.py`)
```python
"""Scratchpad-Service: zwei physisch getrennte Zonen pro User.

user.md  — nur der Mensch (via Web-Konsole)
agent.md — nur der Agent (via write_scratchpad-Tool)

Speicher: data_dir/scratchpad/<user_id>/{user,agent}.md
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

MAX_ZONE_BYTES = 256 * 1024


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

- [ ] **Step 3: backend/routes.py** (aus `api/routes/scratchpad.py`, ohne eigenen Prefix — das Modulsystem mountet unter `/api/modules/scratchpad`)
```python
"""Scratchpad-Endpoints: Mensch-Zone editierbar, Agent-Zone read-only + leerbar."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from .service import ScratchpadTooLarge
from . import service

router = APIRouter()


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

- [ ] **Step 4: backend/tools.py** (read/write-Tools, mit prompt_hint)
```python
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import service
from .service import ScratchpadTooLarge

_READ_DESCRIPTION = (
    "Liest das Scratchpad des Users: Tills handgeschriebene Ideen plus deine "
    "eigenen Agent-Notizen. Nutze es, wenn die Aufgabe auf notierte Ideen Bezug nimmt."
)
_READ_SCHEMA = {"type": "object", "properties": {}, "required": []}
_PROMPT_HINT = (
    "\n\nScratchpad: Till hinterlegt hier Ideen und Notizen. Lies sie mit "
    "`read_scratchpad`, wenn die Aufgabe darauf Bezug nimmt. Eigene Notizen "
    "schreibst du mit `write_scratchpad` — nur in deinen Bereich; Tills Bereich ist tabu."
)

_WRITE_DESCRIPTION = (
    "Schreibt in DEINE Agent-Notiz-Zone des Scratchpads (ersetzt sie komplett). "
    "Tills eigener Bereich ist tabu und kann hierüber nicht verändert werden. "
    "Lies vorher mit read_scratchpad, damit du deine bestehenden Notizen nicht verlierst."
)
_WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string", "description": "Vollständiger neuer Inhalt deiner Agent-Zone (Markdown)."},
    },
    "required": ["content"],
}


async def _read(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(service.get_combined(ctx.user_id))


async def _write(args: dict, ctx: ToolContext) -> ToolResult:
    content = args.get("content")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")
    try:
        service.save_agent(ctx.user_id, content)
    except ScratchpadTooLarge as e:
        return ToolResult.fail(str(e))
    return ToolResult.ok("Agent-Notizen gespeichert.")


READ_TOOL = Tool(name="read_scratchpad", description=_READ_DESCRIPTION, schema=_READ_SCHEMA,
                 execute=_read, category="scratchpad", prompt_hint=_PROMPT_HINT)
WRITE_TOOL = Tool(name="write_scratchpad", description=_WRITE_DESCRIPTION, schema=_WRITE_SCHEMA,
                  execute=_write, category="scratchpad")
```

- [ ] **Step 5: backend/__init__.py**
```python
"""Scratchpad-Modul: per-User Notizzettel (Mensch- + Agent-Zone) + Agent-Tools.

register(ctx) -> API-Router (/api/modules/scratchpad) + read/write_scratchpad-Tools.
Keine Migration (dateibasiert: data_dir/scratchpad/<user>/{user,agent}.md).
"""
from __future__ import annotations

from .routes import router
from .tools import READ_TOOL, WRITE_TOOL


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(READ_TOOL)
    ctx.register_tool(WRITE_TOOL)
```

- [ ] **Step 6: Backend-Syntax prüfen**

Run:
```bash
cd /home/till/hydrahive2-modules
python -c "import ast,glob; [ast.parse(open(f).read()) for f in glob.glob('scratchpad/backend/*.py')]; print('AST OK')"
python -c "import json; json.load(open('scratchpad/manifest.json')); print('JSON OK')"
```
Expected: `AST OK` / `JSON OK`.

- [ ] **Step 7: (Commit erfolgt gebündelt in Task 11 nach E2E-Smoke)**

---

### Task 9: Modul-Frontend (index + Page + api)

**Files:**
- Create: `scratchpad/frontend/api.ts`
- Create: `scratchpad/frontend/ScratchpadPage.tsx`
- Create: `scratchpad/frontend/index.tsx`

- [ ] **Step 1: frontend/api.ts** (BASE auf `/modules/scratchpad`)
```typescript
import { api } from "@/shared/api-client"

export interface ScratchpadData {
  user_content: string
  agent_content: string
}

const BASE = "/modules/scratchpad"

export const scratchpadApi = {
  get: () => api.get<ScratchpadData>(BASE),
  saveUser: (content: string) => api.put<{ saved: boolean }>(BASE, { content }),
  clearAgent: () => api.delete<{ cleared: boolean }>(`${BASE}/agent`),
}
```

- [ ] **Step 2: frontend/ScratchpadPage.tsx** (1:1 aus `frontend/src/features/scratchpad/ScratchpadPage.tsx`; Imports `@/features/chat/Markdown`, `@/shared/colors`, `./api` bleiben — das Modul-Frontend baut innerhalb der Core-Shell, `@/` löst auf `frontend/src/` auf)
```tsx
import { useEffect, useRef, useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { rgbFor } from "@/shared/colors"
import { scratchpadApi } from "./api"

export function ScratchpadPage() {
  const { t } = useTranslation("scratchpad")
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
    if (!confirm(t("clear_confirm"))) return
    scratchpadApi.clearAgent().then(() => setAgentText("")).catch(() => {})
  }

  if (loading) {
    return <div className="h-48 m-6 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
        <span className="text-xs text-zinc-600">{saved ? t("saved") : t("saving")}</span>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-zinc-300">{t("my_ideas")}</h2>
        <div className="grid grid-cols-2 gap-4">
          <textarea
            value={userText}
            onChange={(e) => onChange(e.target.value)}
            placeholder={t("placeholder")}
            className="box min-h-[24rem] px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 font-mono resize-y"
            style={{ "--c": rgbFor("/profile") } as CSSProperties}
          />
          <div className="box overflow-auto min-h-[24rem] px-4 py-3" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
            <Markdown text={userText || t("empty_preview")} />
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-zinc-300">{t("agent_notes")}</h2>
          <span className="text-xs text-zinc-600">{t("agent_notes_hint")}</span>
          <button
            onClick={clearAgent}
            className="ml-auto text-xs text-zinc-500 hover:text-red-400 px-2 py-1 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
          >
            {t("clear")}
          </button>
        </div>
        <div className="box overflow-hidden px-4 py-3" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
          <Markdown text={agentText || t("agent_notes_empty")} />
        </div>
      </section>
    </div>
  )
}
```

- [ ] **Step 3: frontend/index.tsx** (Modul-Contract: routes/nav/i18n; `title` = Nav-Label)
```tsx
import { ScratchpadPage } from "./ScratchpadPage"

export const routes = [{ path: "/scratchpad", element: <ScratchpadPage /> }]
export const nav = [
  { path: "/scratchpad", icon: "StickyNote", labelKey: "scratchpad", group: "working", roles: [] },
]
export const i18n = {
  de: {
    scratchpad: {
      title: "Scratchpad",
      saved: "gespeichert",
      saving: "speichert…",
      my_ideas: "Meine Ideen",
      placeholder: "Ideen, Notizen, Aufgaben (Markdown, `- [ ]` für Checkboxen)…",
      empty_preview: "_(leer)_",
      agent_notes: "Agent-Notizen",
      agent_notes_hint: "(nur der Agent schreibt hier)",
      agent_notes_empty: "_(noch keine Agent-Notizen)_",
      clear: "Leeren",
      clear_confirm: "Agent-Notizen wirklich leeren?",
    },
  },
  en: {
    scratchpad: {
      title: "Scratchpad",
      saved: "saved",
      saving: "saving…",
      my_ideas: "My Ideas",
      placeholder: "Ideas, notes, tasks (Markdown, `- [ ]` for checkboxes)…",
      empty_preview: "_(empty)_",
      agent_notes: "Agent Notes",
      agent_notes_hint: "(only the agent writes here)",
      agent_notes_empty: "_(no agent notes yet)_",
      clear: "Clear",
      clear_confirm: "Really clear agent notes?",
    },
  },
}
```

- [ ] **Step 4: Frontend-Build-Check (Temp-Mount in die Core-Shell)**

Run:
```bash
cd /home/till/claudeneu/frontend
DEST=src/modules/scratchpad
rm -rf "$DEST"; mkdir -p "$DEST"
cp /home/till/hydrahive2-modules/scratchpad/frontend/* "$DEST/"
node scripts/gen-modules.mjs
npm run build && echo "BUILD_OK"
npx eslint "$DEST"; echo "ESLINT_EXIT=$?"
rm -rf "$DEST"; node scripts/gen-modules.mjs
git -C /home/till/claudeneu status --porcelain   # erwartet: leer (kein Leak in den Core)
```
Expected: `BUILD_OK`, `ESLINT_EXIT=0`, leerer git-status.

- [ ] **Step 5: (Commit erfolgt gebündelt in Task 11)**

---

### Task 10: hub.json ergänzen

**Files:**
- Modify: `/home/till/hydrahive2-modules/hub.json`

- [ ] **Step 1: Eintrag ergänzen**

`hub.json` (zusätzlicher Eintrag im `modules`-Array):
```json
{
  "modules": [
    { "id": "example", "name": "Beispiel-Modul", "path": "example" },
    { "id": "notizbuch", "name": "Notizbuch", "path": "notizbuch" },
    { "id": "scratchpad", "name": "Scratchpad", "path": "scratchpad" }
  ]
}
```

- [ ] **Step 2: JSON prüfen**

Run: `cd /home/till/hydrahive2-modules && python -c "import json; print(len(json.load(open('hub.json'))['modules']))"`
Expected: `3`.

---

### Task 11: Lokaler E2E-Smoke über das echte Modulsystem + Push

**Files:**
- Create (throwaway): `core/tests/test_scratchpad_module_smoke.py`

- [ ] **Step 1: Write the smoke test**

`core/tests/test_scratchpad_module_smoke.py`:
```python
"""TEMP-Smoke: Scratchpad-Modul (externes Hub-Repo) über das echte Modulsystem.
Prüft API-Zonen + Tool-Pfad + prompt_hint + default_agent_tools + Datenkontinuität.
Hängt am externen Pfad — nach dem Lauf löschen.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

MODULE_SRC = Path("/home/till/hydrahive2-modules/scratchpad")


def _login(client, user, pw):
    r = client.post("/api/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_scratchpad_module(mod_env):
    shutil.copytree(MODULE_SRC, mod_env / "modules" / "scratchpad")

    # Datenkontinuität: eine user.md VOR dem Laden anlegen
    pre = mod_env / "data" / "scratchpad" / "testuser" / "user.md"
    pre.parent.mkdir(parents=True, exist_ok=True)
    pre.write_text("VORHANDEN-A", encoding="utf-8")

    from hydrahive.api.main import mount_module_routers
    from hydrahive.api.routes.auth import router as auth_router
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY as MODREG
    from hydrahive import tools

    load_all()
    assert MODREG["scratchpad"].loaded is True, MODREG["scratchpad"].error
    tools.register_module_tools(
        [t for m in MODREG.values() if m.loaded and m.ctx for t in m.ctx.tools]
    )
    try:
        # Tools registriert?
        assert "read_scratchpad" in tools.REGISTRY
        assert "write_scratchpad" in tools.REGISTRY
        # default_agent_tools-Flag → in Master-Defaults
        from hydrahive.agents._defaults import DEFAULT_TOOLS
        assert "read_scratchpad" in DEFAULT_TOOLS["master"]
        # prompt_hint vorhanden
        assert tools.REGISTRY["read_scratchpad"].prompt_hint

        app = FastAPI()
        app.include_router(auth_router)
        mount_module_routers(app)
        client = TestClient(app)
        base = "/api/modules/scratchpad"
        h = _login(client, "testuser", "testpass123")

        # Datenkontinuität: vorhandene user.md sichtbar
        r = client.get(base, headers=h)
        assert r.status_code == 200 and r.json()["user_content"] == "VORHANDEN-A"

        # Mensch-Zone schreiben
        assert client.put(base, json={"content": "MENSCH-NEU"}, headers=h).status_code == 200
        assert client.get(base, headers=h).json()["user_content"] == "MENSCH-NEU"

        # Tool-Pfad: write_scratchpad schreibt Agent-Zone, lässt Mensch-Zone unberührt
        from hydrahive.tools.base import ToolContext
        ctx = ToolContext(session_id="s", agent_id="a", user_id="testuser",
                          workspace=Path(mod_env))
        wr = asyncio.run(tools.REGISTRY["write_scratchpad"].execute({"content": "AGENT-X"}, ctx))
        assert wr.success
        body = client.get(base, headers=h).json()
        assert body["agent_content"] == "AGENT-X"
        assert body["user_content"] == "MENSCH-NEU"  # unberührt

        # read_scratchpad liefert beide Zonen kombiniert
        rd = asyncio.run(tools.REGISTRY["read_scratchpad"].execute({}, ctx))
        assert rd.success and "MENSCH-NEU" in rd.output and "AGENT-X" in rd.output

        # Agent-Zone leeren
        assert client.delete(f"{base}/agent", headers=h).status_code == 200
        assert client.get(base, headers=h).json()["agent_content"] == ""

        # Auth-Pflicht
        assert client.get(base).status_code in (401, 403)
    finally:
        tools.register_module_tools([])
```

- [ ] **Step 2: Run the smoke**

Run: `cd /home/till/claudeneu/core && ../.venv/bin/pytest tests/test_scratchpad_module_smoke.py -q`
Expected: PASS.

- [ ] **Step 3: Delete the throwaway + confirm core clean**

Run:
```bash
rm -f /home/till/claudeneu/core/tests/test_scratchpad_module_smoke.py
git -C /home/till/claudeneu status --porcelain   # erwartet: leer
```

- [ ] **Step 4: Commit + push the module to the hub**

```bash
cd /home/till/hydrahive2-modules
git add scratchpad/ hub.json
git commit -m "feat: Scratchpad-Modul (Port aus dem Core) — Mensch-/Agent-Zone, API + Agent-Tools, default_agent_tools"
git push origin main
```

---

# PHASE 3 — Core-Removal (Core-Repo `/home/till/claudeneu`)

> Erst nach erfolgreichem Modul-Smoke + Push. Reihenfolge: erst Backend, dann Frontend, jeweils mit grüner Verifikation.

### Task 12: Scratchpad-Backend aus dem Core entfernen

**Files:**
- Delete: `core/src/hydrahive/scratchpad/` (ganzes Paket)
- Delete: `core/src/hydrahive/tools/read_scratchpad.py`, `core/src/hydrahive/tools/write_scratchpad.py`
- Delete: `core/src/hydrahive/api/routes/scratchpad.py`
- Delete: `core/tests/test_scratchpad_api.py`, `test_scratchpad_prompt.py`, `test_scratchpad_service.py`, `test_scratchpad_tools.py`
- Modify: `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/agents/_defaults.py`, `core/src/hydrahive/api/main.py`

- [ ] **Step 1: Router-Registrierung entfernen**

`core/src/hydrahive/api/main.py` — die `scratchpad`-Router-Import-Zeile und die `app.include_router(scratchpad_router)`-Zeile löschen. (Finde sie mit `grep -n scratchpad core/src/hydrahive/api/main.py`.)

- [ ] **Step 2: Tools aus der Registry-Liste entfernen**

`core/src/hydrahive/tools/__init__.py` — aus dem `from hydrahive.tools import (...)`-Block `read_scratchpad,` und `write_scratchpad,` entfernen; aus `_build_registry()` die Zeilen `read_scratchpad.TOOL,` und `write_scratchpad.TOOL,` entfernen.

- [ ] **Step 3: Aus den Master-Defaults entfernen**

`core/src/hydrahive/agents/_defaults.py` — in `_BASE_TOOLS["master"]` die Einträge `"read_scratchpad", "write_scratchpad",` löschen.

- [ ] **Step 4: Dateien löschen**

```bash
cd /home/till/claudeneu
git rm -r core/src/hydrahive/scratchpad
git rm core/src/hydrahive/tools/read_scratchpad.py core/src/hydrahive/tools/write_scratchpad.py
git rm core/src/hydrahive/api/routes/scratchpad.py
git rm core/tests/test_scratchpad_api.py core/tests/test_scratchpad_prompt.py core/tests/test_scratchpad_service.py core/tests/test_scratchpad_tools.py
```

- [ ] **Step 5: Sicherstellen, dass kein Backend-Code mehr referenziert**

Run: `grep -rn "scratchpad" core/src core/tests`
Expected: **keine Treffer** (alle Referenzen entfernt). Falls Treffer (z.B. in einem anderen Test, der die Master-Defaults prüft): die betroffene Assertion entfernen/anpassen.

- [ ] **Step 6: Volle Backend-Suite grün**

Run: `cd /home/till/claudeneu/core && ../.venv/bin/pytest -q`
Expected: alle grün — beweist, dass nichts verdeckt an Scratchpad hing.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(core): Scratchpad-Backend entfernt (lebt jetzt als Modul)"
```

---

### Task 13: Scratchpad-Frontend aus dem Core entfernen

**Files:**
- Delete: `frontend/src/features/scratchpad/` (api.ts + ScratchpadPage.tsx)
- Delete: `frontend/src/i18n/locales/de/scratchpad.json`, `frontend/src/i18n/locales/en/scratchpad.json`
- Modify: `frontend/src/App.tsx`, `frontend/src/shared/nav-config.ts`, `frontend/src/i18n/index.ts`, `frontend/src/i18n/locales/de/nav.json`, `frontend/src/i18n/locales/en/nav.json`

- [ ] **Step 1: Route entfernen**

`frontend/src/App.tsx` — `import { ScratchpadPage } from "@/features/scratchpad/ScratchpadPage"` und die Zeile `<Route path="scratchpad" element={<ScratchpadPage />} />` löschen.

- [ ] **Step 2: Nav-Eintrag entfernen**

`frontend/src/shared/nav-config.ts` — die Zeile `{ path: "/scratchpad", icon: StickyNote, labelKey: "scratchpad", group: "working" },` löschen. Falls `StickyNote` danach ungenutzt ist, aus dem lucide-Import entfernen (Build/ESLint zeigt es).

- [ ] **Step 3: i18n-Registrierung entfernen**

`frontend/src/i18n/index.ts` — `import deScratchpad ...` und `import enScratchpad ...` löschen; `scratchpad: deScratchpad,` und `scratchpad: enScratchpad,` aus den Resource-Objekten löschen; `"scratchpad"` aus dem `ns: [...]`-Array entfernen.

- [ ] **Step 4: Locale + nav-Label entfernen**

```bash
cd /home/till/claudeneu
git rm frontend/src/i18n/locales/de/scratchpad.json frontend/src/i18n/locales/en/scratchpad.json
git rm -r frontend/src/features/scratchpad
```
`frontend/src/i18n/locales/de/nav.json` und `.../en/nav.json` — den `"scratchpad": "Scratchpad",`-Eintrag unter `items` löschen.

- [ ] **Step 5: Build + Lint grün**

Run:
```bash
cd /home/till/claudeneu/frontend
npm run build && echo "BUILD_OK"
grep -rn "scratchpad" src || echo "KEINE TREFFER"
```
Expected: `BUILD_OK` und `KEINE TREFFER` (kein Scratchpad-Rest im Frontend).

- [ ] **Step 6: Commit**

```bash
cd /home/till/claudeneu
git add -A
git commit -m "refactor(core): Scratchpad-Frontend entfernt (lebt jetzt als Modul)"
```

---

### Task 14: Abschluss — Push + Doku/Memory

- [ ] **Step 1: Push Core**

```bash
cd /home/till/claudeneu
git push origin main
```

- [ ] **Step 2: ROADMAP aktualisieren**

`docs/ROADMAP.md` — in der Portierungs-Kandidaten-Tabelle Scratchpad als erledigt markieren (Status/Häkchen), Reihenfolge-Empfehlung entsprechend kürzen.

- [ ] **Step 3: Commit Doku**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): Scratchpad-Port erledigt"
git push origin main
```

- [ ] **Step 4: Tills Browser-E2E auf .23 (manueller Schritt)**

Auf .23: Core auf neuesten `main` ziehen + Frontend `npm run build` + Dienst-Restart (Scratchpad ist jetzt weg). Dann **System → Module → Scratchpad installieren** → Menüpunkt „Scratchpad" erscheint, Notizen schreiben/speichern/leeren, Agent-Notiz-Zone prüfen. Vorhandene `data_dir/scratchpad/<user>/*.md` sind sofort wieder da. Master-Agenten haben `read_scratchpad`/`write_scratchpad` (default_agent_tools).

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Abdeckung:**
- Phase-1-Vertrag (register_tool / prompt_hint / register_module_tools / manifest-Flag / _defaults / lifespan): Tasks 1–6 ✓
- System-Prompt generisch: Task 1 ✓
- Scratchpad-Modul (Backend/Frontend/hub.json): Tasks 8–10 ✓
- Datenkontinuität (dateibasiert, bleibt): Task 11 Smoke prüft vorhandene user.md ✓
- API-Prefix-Wechsel `/api/scratchpad` → `/api/modules/scratchpad`: Tasks 8/9 ✓
- Core-Removal (Backend + Frontend + Tests, Daten bleiben): Tasks 12–13 ✓
- Tests/Verifikation (Phase-1-TDD, E2E-Smoke, volle Suite, Frontend-Build): Tasks 1–6, 11, 12, 13 ✓
- Validierungstoleranz: durch bestehendes „filter unknown"-Verhalten abgedeckt; Task 12 Step 5 grep + Suite fängt Restbezüge.

**Platzhalter-Scan:** keine TBD/„später"; alle Code-Schritte mit vollständigem Code; alle Befehle mit erwarteter Ausgabe.

**Typ-/Namens-Konsistenz:** `prompt_hint`, `register_module_tools`, `_MODULE_TOOL_NAMES`, `register_tool`, `default_agent_tools`, `_module_default_tool_names`, `READ_TOOL`/`WRITE_TOOL` durchgängig identisch verwendet. Tool-Namen `read_scratchpad`/`write_scratchpad` bleiben gleich (Agent-Configs brechen nicht). Router ohne Prefix (Modulsystem mountet) — konsistent mit Notizbuch.
