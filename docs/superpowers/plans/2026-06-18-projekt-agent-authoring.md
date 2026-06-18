# Projekt-Agent-Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Projekt-Agent kann projekt-gebunden Spezialisten anlegen/konfigurieren und Skills (geteilte Projekt-Bibliothek) bauen/zuweisen.

**Architecture:** Neuer `project`-Skill-Scope (`data_dir/projects/<pid>/skills/`), den alle Agenten eines Projekts automatisch sehen. Fünf Authoring-Tools nur für Projekt-Agenten, hart auf die eigene `project_id` begrenzt; erzeugte Spezialisten erben Tools ⊆ Erzeuger und landen automatisch in `allowed_specialists`.

**Tech Stack:** Python 3.12, FastAPI, pytest. Bestehende Module: `skills/`, `agents/config`, `projects/config`, `tools/`.

## Global Constraints

- Max ~200 Zeilen pro Datei, eine Datei = eine Verantwortung (CLAUDE.md).
- Ein Tool = eine Datei (HH2-Stil), gemeinsamer Code in `_project_authoring.py`.
- Erzwungen: `project_id` + `owner` aus dem Erzeuger, niemals frei wählbar.
- Spezialist-Tools ⊆ Erzeuger-Tools; Authoring-Tools sind nicht zuweisbar.
- Skills nur `project`/`agent`-Scope des eigenen Projekts — nie `system`/`user`.
- Spezialist löschen verboten → nur `status=disabled`.
- Tests zuerst (TDD), häufig committen. Tests laufen mit `.venv/bin/python3 -m pytest` aus dem Repo-Root.

---

### Task 1: `project`-Skill-Scope (Modell + Pfade)

**Files:**
- Modify: `core/src/hydrahive/skills/models.py:12`
- Modify: `core/src/hydrahive/skills/_paths.py`
- Test: `core/tests/test_skills_project_scope.py`

**Interfaces:**
- Produces: `SkillScope` enthält `"project"`; `project_dir(project_id: str) -> Path`; `dir_for("project", project_id)` → `data_dir/projects/<project_id>/skills/`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_skills_project_scope.py
from hydrahive.skills.models import Skill
from hydrahive.skills.loader import save_skill, get_skill
from hydrahive.skills._paths import dir_for


def test_project_scope_dir(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    assert dir_for("project", "proj-1") == tmp_path / "projects" / "proj-1" / "skills"


def test_project_skill_roundtrip(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    ok, _ = save_skill(Skill(
        name="rust-review", description="d", when_to_use="w", body="b",
        scope="project", owner="proj-1",
    ))
    assert ok
    s = get_skill("project", "proj-1", "rust-review")
    assert s and s.name == "rust-review" and s.scope == "project"
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_scope.py -q`
Expected: FAIL (`dir_for` raises `ValueError: unbekannter scope: project`).

- [ ] **Step 3: Implement**

In `core/src/hydrahive/skills/models.py` line 12:
```python
SkillScope = Literal["system", "user", "agent", "project"]
```

In `core/src/hydrahive/skills/_paths.py` add `project_dir` and extend `dir_for`:
```python
def project_dir(project_id: str) -> Path:
    return settings.data_dir / "projects" / project_id / "skills"


def dir_for(scope: SkillScope, owner: str) -> Path:
    if scope == "system":
        return system_dir()
    if scope == "user":
        return user_dir(owner)
    if scope == "agent":
        return agent_dir(owner)
    if scope == "project":
        return project_dir(owner)
    raise ValueError(f"unbekannter scope: {scope}")
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_scope.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/skills/models.py core/src/hydrahive/skills/_paths.py core/tests/test_skills_project_scope.py
git commit -m "feat(skills): project-Scope (geteilte Projekt-Bibliothek)"
```

---

### Task 2: `list_for_agent` mischt Projekt-Skills dazu

**Files:**
- Modify: `core/src/hydrahive/skills/loader.py:78-89`
- Modify callers: `core/src/hydrahive/tools/list_skills.py:23`, `core/src/hydrahive/tools/load_skill.py:32`, `core/src/hydrahive/runner/runner.py` (Aufruf von `load_agent_skills`), `core/src/hydrahive/api/routes/skills.py:42`
- Test: `core/tests/test_skills_project_scope.py` (erweitern)

**Interfaces:**
- Consumes: `dir_for`/`project_dir` aus Task 1.
- Produces: `list_for_agent(agent_id, owner, *, disabled=None, project_id=None)` — mischt Projekt-Skills ein, wenn `project_id` gesetzt. Präzedenz: agent > project > user > system.

- [ ] **Step 1: Failing test (anhängen)**

```python
def test_list_for_agent_includes_project_skills(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    from hydrahive.skills.loader import list_for_agent
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    save_skill(Skill(name="shared", description="d", when_to_use="w", body="b",
                     scope="project", owner="proj-1"))
    with_proj = [s.name for s in list_for_agent("ag-1", "owner-1", project_id="proj-1")]
    without = [s.name for s in list_for_agent("ag-1", "owner-1")]
    assert "shared" in with_proj
    assert "shared" not in without
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_scope.py::test_list_for_agent_includes_project_skills -q`
Expected: FAIL (`list_for_agent() got an unexpected keyword argument 'project_id'`).

- [ ] **Step 3: Implement**

Replace `core/src/hydrahive/skills/loader.py` lines 78-89:
```python
def list_for_agent(
    agent_id: str,
    owner: str,
    *,
    disabled: list[str] | None = None,
    project_id: str | None = None,
) -> list[Skill]:
    """Merge system + user + project + agent. Präzedenz bei Namens-Kollision:
    agent > project > user > system. `disabled` blendet Skill-Namen aus."""
    from hydrahive.skills._paths import project_dir
    bag: dict[str, Skill] = {}
    for s in _list_dir(system_dir(), "system", "system"):
        bag[s.name] = s
    for s in _list_dir(user_dir(owner), "user", owner):
        bag[s.name] = s
    if project_id:
        for s in _list_dir(project_dir(project_id), "project", project_id):
            bag[s.name] = s
    for s in _list_dir(agent_dir(agent_id), "agent", agent_id):
        bag[s.name] = s
    skip = set(disabled or [])
    return [s for n, s in sorted(bag.items()) if n not in skip]
```

In `core/src/hydrahive/tools/list_skills.py:23` and `load_skill.py:32`, pass project_id (the `agent` dict is already loaded above each call):
```python
    skills = list_for_agent(ctx.agent_id, owner, disabled=disabled, project_id=agent.get("project_id"))
```

In `core/src/hydrahive/api/routes/skills.py:42` pass the project_id:
```python
        return [_serialize(s) for s in list_for_agent(agent_id, agent["owner"] or username, disabled=disabled, project_id=agent.get("project_id"))]
```

In `core/src/hydrahive/runner/runner.py:126`, ergänze `project_id`:
```python
    agent_skills = load_agent_skills(agent["id"], agent["owner"], disabled=agent.get("disabled_skills") or [], project_id=agent.get("project_id"))
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_scope.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/skills/loader.py core/src/hydrahive/tools/list_skills.py core/src/hydrahive/tools/load_skill.py core/src/hydrahive/api/routes/skills.py core/src/hydrahive/runner/runner.py core/tests/test_skills_project_scope.py
git commit -m "feat(skills): Projekt-Skills im list_for_agent-Merge"
```

---

### Task 3: Skills-REST-Route — `project`-Scope + Mitglieds-Auth

**Files:**
- Modify: `core/src/hydrahive/api/routes/skills.py` (Handler `create_or_update`, `get_skill_endpoint`, `delete_skill_endpoint`, Listing)
- Test: `core/tests/test_skills_project_route.py`

**Interfaces:**
- Consumes: `projects.config.get`, `projects.members`.
- Produces: REST akzeptiert `scope="project"`, nur wenn der User Owner/Member des Projekts ist (sonst 403).

- [ ] **Step 1: Failing test**

```python
# core/tests/test_skills_project_route.py
def test_non_member_cannot_write_project_skill(client, auth_headers, monkeypatch):
    from hydrahive.projects import config as pc
    monkeypatch.setattr(pc, "get", lambda pid: {"id": pid, "owner": "someone_else", "members": []})
    r = client.post("/api/skills/project", headers=auth_headers, json={
        "owner": "proj-x", "name": "x", "description": "d", "when_to_use": "w", "body": "b",
    })
    assert r.status_code == 403
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_route.py -q`
Expected: FAIL (Route akzeptiert project noch nicht / 422 statt 403).

- [ ] **Step 3: Implement**

In `core/src/hydrahive/api/routes/skills.py`, im `create_or_update`-Handler den `project`-Zweig ergänzen (parallel zu `agent`/`user`), mit Mitglieds-Check:
```python
    elif scope == "project":
        from hydrahive.projects import config as project_config
        proj = project_config.get(owner)  # owner == project_id
        if not proj:
            raise coded(404, "project_not_found")
        members = proj.get("members", [])
        if proj.get("owner") != username and username not in members and role != "admin":
            raise coded(403, "forbidden")
```
Gleichen Check in `get_skill_endpoint` und `delete_skill_endpoint` für `scope == "project"` spiegeln. Im Listing-Endpoint `scope in ("project", "all")` nur eigene Projekte einbeziehen (über `project_config.list_for_user(username)`).

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_route.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/api/routes/skills.py core/tests/test_skills_project_route.py
git commit -m "feat(skills): REST-Route fuer project-Scope mit Mitglieds-Auth"
```

---

### Task 4: Authoring-Guard (gemeinsamer Helfer)

**Files:**
- Create: `core/src/hydrahive/tools/_project_authoring.py`
- Test: `core/tests/test_project_authoring_guard.py`

**Interfaces:**
- Produces:
  - `AUTHORING_TOOLS: frozenset[str]` — Namen der Authoring-Tools (nicht zuweisbar).
  - `resolve_project_agent(ctx) -> tuple[dict, str]` — liefert `(agent_cfg, project_id)` oder wirft `AuthoringError`.
  - `bounded_tools(requested: list[str], creator_tools: list[str]) -> list[str]` — Schnittmenge mit Erzeuger-Tools, ohne Authoring-Tools.
  - `class AuthoringError(Exception)`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_project_authoring_guard.py
import pytest
from hydrahive.tools import _project_authoring as pa
from hydrahive.tools.base import ToolContext
from pathlib import Path


def _ctx(agent_id="a"):
    return ToolContext(session_id="s", agent_id=agent_id, user_id="u", workspace=Path("/tmp"))


def test_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "a", "type": "master", "owner": "u"})
    with pytest.raises(pa.AuthoringError):
        pa.resolve_project_agent(_ctx())


def test_resolves_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "a", "type": "project", "owner": "u", "project_id": "P"})
    agent, pid = pa.resolve_project_agent(_ctx())
    assert pid == "P"


def test_bounded_tools_intersects_and_strips_authoring():
    out = pa.bounded_tools(["file_read", "shell_exec", "create_specialist"], ["file_read", "list_skills"])
    assert out == ["file_read"]
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_project_authoring_guard.py -q`
Expected: FAIL (`ModuleNotFoundError: ... _project_authoring`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/_project_authoring.py
"""Gemeinsame Sicherheits-Bausteine der Projekt-Authoring-Tools.

Erzwingt: nur Projekt-Agenten dürfen authoren; erzeugte Spezialisten erben
höchstens die Tools ihres Erzeugers und nie die Authoring-Tools selbst."""
from __future__ import annotations

from hydrahive.tools.base import ToolContext

AUTHORING_TOOLS: frozenset[str] = frozenset({
    "create_specialist", "configure_specialist", "list_specialists",
    "write_skill", "delete_skill",
})


class AuthoringError(Exception):
    """Aufrufer ist kein berechtigter Projekt-Agent."""


def resolve_project_agent(ctx: ToolContext) -> tuple[dict, str]:
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(ctx.agent_id)
    if not agent:
        raise AuthoringError("Agent nicht gefunden")
    if agent.get("type") != "project":
        raise AuthoringError("Nur Projekt-Agenten dürfen Spezialisten/Skills anlegen")
    pid = agent.get("project_id")
    if not pid:
        raise AuthoringError("Projekt-Agent ohne project_id")
    return agent, pid


def bounded_tools(requested: list[str], creator_tools: list[str]) -> list[str]:
    creator = set(creator_tools)
    return [t for t in requested if t in creator and t not in AUTHORING_TOOLS]
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_project_authoring_guard.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/_project_authoring.py core/tests/test_project_authoring_guard.py
git commit -m "feat(tools): Authoring-Guard (Projekt-Agent-Check + Tools-Subset)"
```

---

### Task 5: `create_specialist`-Tool

**Files:**
- Create: `core/src/hydrahive/tools/create_specialist.py`
- Modify: `core/src/hydrahive/tools/__init__.py` (Import + Registrierung), `core/src/hydrahive/agents/_defaults.py` (`project`-Liste)
- Test: `core/tests/test_create_specialist_tool.py`

**Interfaces:**
- Consumes: `resolve_project_agent`, `bounded_tools` (Task 4); `agents.config.create`; `projects.config.get/update`.
- Produces: Tool `create_specialist` (args: `name`, `description?`, `llm_model?`, `tools?`); erzeugt type=specialist mit project_id/owner des Erzeugers, Tools via `bounded_tools`, trägt id in `allowed_specialists` ein.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_create_specialist_tool.py
import asyncio
from pathlib import Path
from hydrahive.tools.base import ToolContext
from hydrahive.tools import create_specialist as cs


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_create_specialist_forces_project_and_subsets_tools(monkeypatch):
    creator = {"id": "proj-agent", "type": "project", "owner": "u",
               "project_id": "P", "llm_model": "claude-sonnet-4-6",
               "tools": ["file_read", "shell_exec", "create_specialist"]}
    created = {}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: creator)
    monkeypatch.setattr("hydrahive.agents.config.create",
                        lambda *a, **k: created.update(k) or {"id": "spec-1", **k})
    monkeypatch.setattr("hydrahive.projects.config.get",
                        lambda pid: {"id": pid, "allowed_specialists": []})
    captured = {}
    monkeypatch.setattr("hydrahive.projects.config.update",
                        lambda pid, **ch: captured.update(ch))

    res = asyncio.run(cs.TOOL.execute(
        {"name": "rust-reviewer", "tools": ["file_read", "shell_exec", "create_specialist", "todo_write"]},
        _ctx()))

    assert res.success
    assert created["project_id"] == "P"
    assert created["owner"] == "u"
    assert created["agent_type"] == "specialist"
    # create_specialist (authoring) + todo_write (nicht beim Erzeuger) gefiltert
    assert set(created["tools"]) == {"file_read", "shell_exec"}
    assert "spec-1" in captured["allowed_specialists"]


def test_create_specialist_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "m", "type": "master", "owner": "u"})
    res = asyncio.run(cs.TOOL.execute({"name": "x"}, _ctx()))
    assert not res.success
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_create_specialist_tool.py -q`
Expected: FAIL (`ModuleNotFoundError: ... create_specialist`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/create_specialist.py
from __future__ import annotations

from hydrahive.agents._defaults import (
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_THINKING_BUDGET, DEFAULT_TOOLS,
)
from hydrahive.tools._project_authoring import AuthoringError, bounded_tools, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Legt einen neuen Spezialisten in DEINEM Projekt an (du musst Projekt-Agent sein). "
    "Der Spezialist erbt höchstens deine eigenen Tools und wird automatisch für die "
    "Delegation per ask_agent freigegeben."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Name des Spezialisten"},
        "description": {"type": "string", "description": "Wofür er zuständig ist"},
        "llm_model": {"type": "string", "description": "Optional; Default: dein eigenes Modell"},
        "tools": {"type": "array", "items": {"type": "string"},
                  "description": "Optional; Teilmenge deiner Tools. Default: Spezialist-Standard."},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    try:
        creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    name = (args.get("name") or "").strip()
    if not name:
        return ToolResult.fail("name fehlt")

    requested = args.get("tools")
    tools = bounded_tools(requested, creator.get("tools", [])) if requested else list(DEFAULT_TOOLS["specialist"])
    model = (args.get("llm_model") or creator.get("llm_model") or "").strip()

    try:
        cfg = agent_config.create(
            agent_type="specialist",
            name=name,
            llm_model=model,
            tools=tools,
            owner=creator.get("owner"),
            created_by=creator.get("id"),
            description=args.get("description", ""),
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
            thinking_budget=DEFAULT_THINKING_BUDGET,
            project_id=pid,
        )
    except Exception as e:
        return ToolResult.fail(f"Anlegen fehlgeschlagen: {e}")

    proj = project_config.get(pid)
    allowed = list((proj or {}).get("allowed_specialists", []))
    if cfg["id"] not in allowed:
        project_config.update(pid, allowed_specialists=allowed + [cfg["id"]])

    return ToolResult.ok({"id": cfg["id"], "name": name, "tools": tools, "project_id": pid})


TOOL = Tool(name="create_specialist", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
```

In `core/src/hydrahive/tools/__init__.py`: importiere `create_specialist` und füge `create_specialist.TOOL` zur Registry-Liste hinzu (analog zu den bestehenden Tools, **unbedingt** zu den nicht-optionalen Tools).

In `core/src/hydrahive/agents/_defaults.py` die `"project"`-Liste um `"create_specialist"` ergänzen.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_create_specialist_tool.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/create_specialist.py core/src/hydrahive/tools/__init__.py core/src/hydrahive/agents/_defaults.py core/tests/test_create_specialist_tool.py
git commit -m "feat(tools): create_specialist (projekt-gebunden, tools-bounded, auto-allowed)"
```

---

### Task 6: `configure_specialist`-Tool

**Files:**
- Create: `core/src/hydrahive/tools/configure_specialist.py`
- Modify: `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/agents/_defaults.py`
- Test: `core/tests/test_configure_specialist_tool.py`

**Interfaces:**
- Consumes: `resolve_project_agent`, `bounded_tools`; `agents.config.get/update/set_system_prompt`.
- Produces: Tool `configure_specialist` (args: `agent_id`, optional `llm_model`/`tools`/`system_prompt`/`description`/`status`). Ändert nur Spezialisten mit gleicher `project_id`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_configure_specialist_tool.py
import asyncio
from pathlib import Path
from hydrahive.tools.base import ToolContext
from hydrahive.tools import configure_specialist as conf


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_rejects_cross_project_target(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u",
                    "project_id": "P", "tools": ["file_read"]}
        return {"id": "spec-x", "type": "specialist", "project_id": "OTHER"}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    res = asyncio.run(conf.TOOL.execute({"agent_id": "spec-x", "status": "disabled"}, _ctx()))
    assert not res.success


def test_configures_own_project_specialist(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u",
                    "project_id": "P", "tools": ["file_read", "shell_exec"]}
        return {"id": "spec-1", "type": "specialist", "project_id": "P"}
    captured = {}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    monkeypatch.setattr("hydrahive.agents.config.update",
                        lambda aid, **ch: captured.update({"id": aid, **ch}))
    res = asyncio.run(conf.TOOL.execute(
        {"agent_id": "spec-1", "tools": ["file_read", "todo_write"], "status": "disabled"}, _ctx()))
    assert res.success
    assert captured["id"] == "spec-1"
    assert captured["tools"] == ["file_read"]   # todo_write nicht beim Erzeuger → gefiltert
    assert captured["status"] == "disabled"
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_configure_specialist_tool.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/configure_specialist.py
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, bounded_tools, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Ändert einen Spezialisten DEINES Projekts (Modell, Tools, System-Prompt, "
    "Beschreibung, status aktiv/disabled). Tools werden auf deine eigenen begrenzt."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "agent_id": {"type": "string"},
        "llm_model": {"type": "string"},
        "tools": {"type": "array", "items": {"type": "string"}},
        "system_prompt": {"type": "string"},
        "description": {"type": "string"},
        "status": {"type": "string", "enum": ["active", "disabled"]},
    },
    "required": ["agent_id"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    try:
        creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    target_id = (args.get("agent_id") or "").strip()
    target = agent_config.get(target_id)
    if not target or target.get("type") != "specialist" or target.get("project_id") != pid:
        return ToolResult.fail("Spezialist nicht in deinem Projekt gefunden")

    changes: dict = {}
    if "llm_model" in args:
        changes["llm_model"] = args["llm_model"]
    if "tools" in args:
        changes["tools"] = bounded_tools(args["tools"], creator.get("tools", []))
    if "description" in args:
        changes["description"] = args["description"]
    if "status" in args:
        changes["status"] = args["status"]

    if changes:
        agent_config.update(target_id, **changes)
    if args.get("system_prompt"):
        agent_config.set_system_prompt(target_id, args["system_prompt"])

    return ToolResult.ok({"id": target_id, "updated": sorted([*changes, *(["system_prompt"] if args.get("system_prompt") else [])])})


TOOL = Tool(name="configure_specialist", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
```

Registrierung in `tools/__init__.py` + `"configure_specialist"` in `_defaults.py` `project`-Liste.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_configure_specialist_tool.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/configure_specialist.py core/src/hydrahive/tools/__init__.py core/src/hydrahive/agents/_defaults.py core/tests/test_configure_specialist_tool.py
git commit -m "feat(tools): configure_specialist (eigenes Projekt, tools-bounded)"
```

---

### Task 7: `list_specialists`-Tool (+ Authoring-Prompt-Hint)

**Files:**
- Create: `core/src/hydrahive/tools/list_specialists.py`
- Modify: `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/agents/_defaults.py`
- Test: `core/tests/test_list_specialists_tool.py`

**Interfaces:**
- Consumes: `resolve_project_agent`; `agents.config.list_all`.
- Produces: Tool `list_specialists` (keine args) → Spezialisten des eigenen Projekts. Trägt einen `prompt_hint`, der dem Projekt-Agenten die Authoring-Fähigkeit bekannt macht (schließt Discovery-Lücke).

- [ ] **Step 1: Failing test**

```python
# core/tests/test_list_specialists_tool.py
import asyncio
from pathlib import Path
from hydrahive.tools.base import ToolContext
from hydrahive.tools import list_specialists as ls


def test_lists_only_own_project_specialists(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    monkeypatch.setattr("hydrahive.agents.config.list_all", lambda: [
        {"id": "s1", "type": "specialist", "project_id": "P", "name": "A", "tools": []},
        {"id": "s2", "type": "specialist", "project_id": "OTHER", "name": "B", "tools": []},
        {"id": "m", "type": "master", "project_id": None, "name": "M", "tools": []},
    ])
    ctx = ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))
    res = asyncio.run(ls.TOOL.execute({}, ctx))
    assert res.success
    ids = {s["id"] for s in res.output["specialists"]}
    assert ids == {"s1"}


def test_tool_has_authoring_prompt_hint():
    assert ls.TOOL.prompt_hint and "Spezialist" in ls.TOOL.prompt_hint
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_list_specialists_tool.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/list_specialists.py
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = "Listet die Spezialisten deines Projekts (id, name, tools, status)."
_SCHEMA = {"type": "object", "properties": {}, "required": []}

_PROMPT_HINT = (
    "\n\nDu kannst dein Projekt selbst gestalten: lege mit `create_specialist` "
    "Spezialisten an, gib ihnen mit `write_skill` (Projekt-Bibliothek) Fähigkeiten, "
    "sieh sie mit `list_specialists` und delegiere via `ask_agent`."
)


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    try:
        _creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))
    out = [
        {"id": a["id"], "name": a.get("name", ""), "tools": a.get("tools", []),
         "status": a.get("status", "active")}
        for a in agent_config.list_all()
        if a.get("type") == "specialist" and a.get("project_id") == pid
    ]
    return ToolResult.ok({"specialists": out, "count": len(out)})


TOOL = Tool(name="list_specialists", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents", prompt_hint=_PROMPT_HINT)
```

Registrierung in `tools/__init__.py` + `"list_specialists"` in `_defaults.py` `project`-Liste.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_list_specialists_tool.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/list_specialists.py core/src/hydrahive/tools/__init__.py core/src/hydrahive/agents/_defaults.py core/tests/test_list_specialists_tool.py
git commit -m "feat(tools): list_specialists + Authoring-Prompt-Hint (schliesst Discovery-Luecke)"
```

---

### Task 8: `write_skill`-Tool

**Files:**
- Create: `core/src/hydrahive/tools/write_skill.py`
- Modify: `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/agents/_defaults.py`
- Test: `core/tests/test_write_skill_tool.py`

**Interfaces:**
- Consumes: `resolve_project_agent`; `skills.save_skill`, `skills.models.Skill`, `agents.config.get`.
- Produces: Tool `write_skill` (args: `name`, `description`, `when_to_use`, `body`, optional `specialist_id`). Default-Scope `project` (owner=project_id); mit `specialist_id` → `agent`-Scope dieses Spezialisten (muss im Projekt sein). Nie `system`/`user`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_write_skill_tool.py
import asyncio
from pathlib import Path
from hydrahive.tools.base import ToolContext
from hydrahive.tools import write_skill as ws


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_write_skill_defaults_to_project_scope(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    saved = {}
    def _save(skill):
        saved["scope"] = skill.scope
        saved["owner"] = skill.owner
        saved["name"] = skill.name
        return True, ""
    monkeypatch.setattr("hydrahive.skills.save_skill", _save)
    res = asyncio.run(ws.TOOL.execute(
        {"name": "rust-review", "description": "d", "when_to_use": "w", "body": "b"}, _ctx()))
    assert res.success
    assert saved == {"scope": "project", "owner": "P", "name": "rust-review"}


def test_write_skill_agent_scope_requires_project_member(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"}
        return {"id": "spec-x", "type": "specialist", "project_id": "OTHER"}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    res = asyncio.run(ws.TOOL.execute(
        {"name": "x", "description": "d", "when_to_use": "w", "body": "b", "specialist_id": "spec-x"}, _ctx()))
    assert not res.success
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_write_skill_tool.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/write_skill.py
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Legt einen Skill an oder bearbeitet ihn. Standard: Projekt-Bibliothek (alle "
    "Agenten deines Projekts sehen ihn). Mit `specialist_id` nur für genau diesen "
    "Spezialisten deines Projekts."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "kleinbuchstaben, a-z0-9_-"},
        "description": {"type": "string"},
        "when_to_use": {"type": "string"},
        "body": {"type": "string", "description": "Markdown-Anleitung"},
        "specialist_id": {"type": "string", "description": "Optional; Skill nur für diesen Spezialisten"},
    },
    "required": ["name", "description", "when_to_use", "body"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import save_skill
    from hydrahive.skills.models import Skill
    try:
        _creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    spec_id = (args.get("specialist_id") or "").strip()
    if spec_id:
        target = agent_config.get(spec_id)
        if not target or target.get("type") != "specialist" or target.get("project_id") != pid:
            return ToolResult.fail("Spezialist nicht in deinem Projekt gefunden")
        scope, owner = "agent", spec_id
    else:
        scope, owner = "project", pid

    ok, err = save_skill(Skill(
        name=(args.get("name") or "").strip(),
        description=args.get("description", ""),
        when_to_use=args.get("when_to_use", ""),
        body=args.get("body", ""),
        scope=scope, owner=owner,
    ))
    if not ok:
        return ToolResult.fail(f"Skill speichern fehlgeschlagen: {err}")
    return ToolResult.ok({"name": args["name"], "scope": scope})


TOOL = Tool(name="write_skill", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
```

Registrierung in `tools/__init__.py` + `"write_skill"` in `_defaults.py` `project`-Liste.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_write_skill_tool.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/write_skill.py core/src/hydrahive/tools/__init__.py core/src/hydrahive/agents/_defaults.py core/tests/test_write_skill_tool.py
git commit -m "feat(tools): write_skill (Projekt-Bibliothek / Spezialist-Scope)"
```

---

### Task 9: `delete_skill`-Tool

**Files:**
- Create: `core/src/hydrahive/tools/delete_skill_tool.py`
- Modify: `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/agents/_defaults.py`
- Test: `core/tests/test_delete_skill_tool.py`

**Interfaces:**
- Consumes: `resolve_project_agent`; `skills.delete_skill`; `agents.config.get`.
- Produces: Tool `delete_skill` (args: `name`, optional `specialist_id`). Löscht `project`-Skill (Default) oder `agent`-Skill eines Projekt-Spezialisten. Nie `system`/`user`.

- [ ] **Step 1: Failing test**

```python
# core/tests/test_delete_skill_tool.py
import asyncio
from pathlib import Path
from hydrahive.tools.base import ToolContext
from hydrahive.tools import delete_skill_tool as dst


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_delete_project_skill(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    deleted = {}
    monkeypatch.setattr("hydrahive.skills.delete_skill",
                        lambda scope, owner, name: deleted.update({"scope": scope, "owner": owner, "name": name}) or True)
    res = asyncio.run(dst.TOOL.execute({"name": "rust-review"}, _ctx()))
    assert res.success
    assert deleted == {"scope": "project", "owner": "P", "name": "rust-review"}


def test_delete_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "m", "type": "master", "owner": "u"})
    res = asyncio.run(dst.TOOL.execute({"name": "x"}, _ctx()))
    assert not res.success
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python3 -m pytest core/tests/test_delete_skill_tool.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# core/src/hydrahive/tools/delete_skill_tool.py
from __future__ import annotations

from hydrahive.tools._project_authoring import AuthoringError, resolve_project_agent
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Löscht einen Skill deines Projekts: Default Projekt-Bibliothek, mit "
    "`specialist_id` den Agent-Skill dieses Spezialisten."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "specialist_id": {"type": "string"},
    },
    "required": ["name"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    from hydrahive.agents import config as agent_config
    from hydrahive.skills import delete_skill
    try:
        _creator, pid = resolve_project_agent(ctx)
    except AuthoringError as e:
        return ToolResult.fail(str(e))

    spec_id = (args.get("specialist_id") or "").strip()
    if spec_id:
        target = agent_config.get(spec_id)
        if not target or target.get("type") != "specialist" or target.get("project_id") != pid:
            return ToolResult.fail("Spezialist nicht in deinem Projekt gefunden")
        scope, owner = "agent", spec_id
    else:
        scope, owner = "project", pid

    ok = delete_skill(scope, owner, (args.get("name") or "").strip())
    if not ok:
        return ToolResult.fail("Skill nicht gefunden")
    return ToolResult.ok({"deleted": args["name"], "scope": scope})


TOOL = Tool(name="delete_skill", description=_DESCRIPTION, schema=_SCHEMA,
            execute=_execute, category="agents")
```

Registrierung in `tools/__init__.py` + `"delete_skill"` in `_defaults.py` `project`-Liste.

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python3 -m pytest core/tests/test_delete_skill_tool.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/tools/delete_skill_tool.py core/src/hydrahive/tools/__init__.py core/src/hydrahive/agents/_defaults.py core/tests/test_delete_skill_tool.py
git commit -m "feat(tools): delete_skill (Projekt-/Spezialist-Scope)"
```

---

### Task 10: Integrations-Smoke + Lint + Gesamttests

**Files:**
- Test: alle neuen + bestehende AgentLink/Skill/Tool-Tests.

- [ ] **Step 1: Lint**

Run: `.venv/bin/python3 -m ruff check core/src/hydrahive/tools/ core/src/hydrahive/skills/ core/src/hydrahive/agents/_defaults.py`
Expected: All checks passed.

- [ ] **Step 2: Registry-Smoke (Tools tatsächlich registriert + im project-Default)**

Run:
```bash
HH_CONFIG_DIR=/home/till/.hh2-dev/config HH_DATA_DIR=/home/till/.hh2-dev/data PYTHONPATH=core/src \
.venv/bin/python3 -c "
from hydrahive.tools import REGISTRY
from hydrahive.agents._defaults import DEFAULT_TOOLS
need = {'create_specialist','configure_specialist','list_specialists','write_skill','delete_skill'}
assert need <= set(REGISTRY), need - set(REGISTRY)
assert need <= set(DEFAULT_TOOLS['project']), need - set(DEFAULT_TOOLS['project'])
assert not (need & set(DEFAULT_TOOLS['specialist'])), 'Authoring darf nicht im Spezialist-Default sein'
print('registry+defaults OK')
"
```
Expected: `registry+defaults OK`.

- [ ] **Step 3: Gesamttest-Lauf**

Run: `.venv/bin/python3 -m pytest core/tests/test_skills_project_scope.py core/tests/test_skills_project_route.py core/tests/test_project_authoring_guard.py core/tests/test_create_specialist_tool.py core/tests/test_configure_specialist_tool.py core/tests/test_list_specialists_tool.py core/tests/test_write_skill_tool.py core/tests/test_delete_skill_tool.py core/tests/test_agentlink_handoff_security.py -q`
Expected: alle PASS.

- [ ] **Step 4: Commit (Plan + Spec-Doc)**

```bash
git add docs/superpowers/specs/2026-06-18-projekt-agent-authoring-design.md docs/superpowers/plans/2026-06-18-projekt-agent-authoring.md
git commit -m "docs: Spec + Plan Projekt-Agent-Authoring (Feature 1)"
```

---

## Offen nach Feature 1 (separat, mit Tills OK)

- **SPEC.md-Ergänzung** (Standalone-Commit, Regel #8): kurzer Absatz beim Projekt-Agent.
- **UI**: Anzeige/Bearbeitung der Projekt-Skills + vom Agent erzeugter Spezialisten im Projekt-Panel.
- **Feature 2**: Spezialisten/Skills als Vorlagen für andere User (Cross-User-Sharing).
