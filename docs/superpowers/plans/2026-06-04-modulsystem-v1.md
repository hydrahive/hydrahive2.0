# Modulsystem v1 — Implementierungsplan (Sub-Projekt 1: Framework + Template-Modul)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Task für Task umzusetzen. Steps nutzen Checkbox-Syntax (`- [ ]`).

**Goal:** Voll-Stack-Module per Knopf installier-/deinstallierbar (UI+API+Migrationen+Dienst), bewiesen mit einem Minimal-Template-Modul — Deinstall entfernt alles außer den Modul-Daten.

**Architecture:** Parallel-System zum Plugin-System (`modules/` mit Loader/Registry/Installer/Hub nach Plugin-Muster), breiterer `ModuleContext` (Router/Migrationen/Dienst). Frontend: Modul deklariert `{routes,nav,i18n}`, ein node-`prebuild`-Codegen webt installierte Module beim `npm run build` ein; Core nur einmal angefasst. Install = pull→kopieren→build→`.restart_request`; Deinstall umgekehrt, Daten bleiben.

**Tech Stack:** Python 3.12 / FastAPI / SQLite / importlib · React+TS+Vite · git-Hub-Cache · systemd-Path-Watcher (`.restart_request`).

**Spec:** `docs/superpowers/specs/2026-06-04-modulsystem-v1-design.md`.

---

## File-Structure (gesamt Sub-Projekt 1)

```
core/src/hydrahive/modules/
  __init__.py          # [T4] Fassade: load_all, REGISTRY
  manifest.py          # [T3] ModuleManifest (parse/validate manifest.json)
  registry.py          # [T4] LoadedModule + REGISTRY
  context.py           # [T4] ModuleContext (register_router/migrations/service)
  migrations.py        # [T2] apply_module_migrations + module_schema_version
  loader.py            # [T5] load_all() (importlib, Isolation, ruft Migrationen)
  hub_client.py        # [T7] git-Hub-Cache (Muster plugins/hub_client.py)
  installer.py         # [T8/T11] install/uninstall (copytree/rmtree + build + restart + Dienst)
core/src/hydrahive/db/migrations/027_module_schema_version.sql   # [T2]
core/src/hydrahive/settings/_modules.py                          # [T1] Settings-Mixin
core/src/hydrahive/api/routes/modules.py                         # [T12] Admin-Endpoints
core/src/hydrahive/api/main.py                                   # [T6/T12] load_all + Router
frontend/scripts/gen-modules.mjs                                 # [T9] Codegen (prebuild)
frontend/src/modules/index.generated.ts                          # [T9] generiert (gitignored)
frontend/src/shared/module-icon.ts                               # [T10] Icon-String→lucide-Resolver
frontend/src/App.tsx · shared/nav-config.ts · i18n/index.ts      # [T10] einmalige Hooks
frontend/src/features/modules/{api,types,ModulesPage,...}        # [T13] Admin-UI
modules/example/                                                 # [T14] Template-Modul (Referenz)
```

---

## Vorlagen-Katalog (verbindlich, verifiziert)

- Plugin-Loader importlib: `core/src/hydrahive/plugins/loader.py:43-66` (spec_from_file_location, sys.path, sys.modules).
- Plugin-Installer copytree/rmtree + `restart_recommended`: `plugins/installer.py:55-96`.
- Plugin-Hub git-Cache: `plugins/hub_client.py:38-67` (`git clone --depth=1 --filter=blob:none`, `git pull --ff-only`, `hub.json`).
- Migrations-Runner: `db/migrations.py:14-59` (`schema_version`, `glob("*.sql")` sortiert, version=int(name.split("_",1)[0])).
- DB-Zugriff: `with db() as conn` (`db/connection.py`); `now_iso()` aus `hydrahive.utils` (s. `db/migrations.py`-Import).
- Settings-Mixin + `env_or_override`: `settings/_mail.py` + Komposition `settings/settings.py:30-46`.
- API-Router + Auth: `routes/federation.py` (`APIRouter(prefix=...)`, `require_auth`/`require_admin`), Registrierung `api/main.py:101-129`.
- Streamed-Install-Log (Frontend+Backend): `features/extensions/api.ts:16-59` (`streamAction`, fetch+ReadableStream) + `routes/admin_extensions`-SSE (Muster). 
- Restart-Trigger: `routes/system_admin.py:29` (`RESTART_TRIGGER = settings.data_dir / ".restart_request"`).
- Test-Gotcha: hydrahive-Imports in Tests **lazy** halten (settings.data_dir-Freeze).

---

## Test-Isolation (VERBINDLICH für alle Tasks)

> **Verifiziert (`conftest.py:48-54`):** `setup_test_env` ist **session-scoped + autouse** und setzt `HH_DATA_DIR`/`HH_CONFIG_DIR` einmalig. `settings`-Pfade sind `cached_property` → nach dem ersten Zugriff **eingefroren**. Deshalb ist `monkeypatch.setenv("HH_DATA_DIR", …)` in einem einzelnen Test **wirkungslos**. Das Repo-Muster (`test_research_apis.py:35-36`) ist `monkeypatch.setattr(settings, "<pfad>", tmp, raising=False)`. `db()`/`init_db()` lesen `settings.sessions_db` **pro Aufruf** (`connection.py:19/38`) → Umbiegen per setattr ergibt eine frische Test-DB.
>
> **Niemals** `monkeypatch.setenv("HH_DATA_DIR", …)` in Modul-Tests verwenden. Stattdessen die folgende Fixture.

### Task 0: Shared Test-Fixture `mod_env`

**Files:** Modify `core/tests/conftest.py` (Fixture anhängen) · keine eigene Test-Datei

- [ ] **Step 1: Fixture ergänzen** in `core/tests/conftest.py`:
```python
@pytest.fixture
def mod_env(tmp_path, monkeypatch):
    """Isolierte Modul-Umgebung: frische DB + repointete Modul-Pfade (umgeht den
    session-weiten settings-Freeze, Muster test_research_apis.py)."""
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "test.db", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    monkeypatch.setattr(settings, "modules_dir", tmp_path / "modules", raising=False)
    monkeypatch.setattr(settings, "base_dir", tmp_path / "repo", raising=False)
    monkeypatch.setattr(settings, "module_hub_cache", tmp_path / "hub", raising=False)
    (tmp_path / "data").mkdir()
    (tmp_path / "modules").mkdir()
    from hydrahive.db import init_db
    init_db()                       # frische DB inkl. Migration 027 (nach Task 2)
    return tmp_path
```
- [ ] **Step 2: Smoke** (nachdem Task 2 die 027-Migration gebaut hat): `pytest core/tests/test_module_migrations.py -v` nutzt `mod_env` und ist grün. (Vor Task 2 hat `mod_env` noch keine 027 — das ist ok, die Fixture wird erstmals in Task 2 konsumiert.)
- [ ] **Step 3: Commit:** `git add core/tests/conftest.py && git commit -m "test(modules): mod_env-Fixture (isolierte DB + Modul-Pfade)"`.

> **Alle folgenden Task-Tests** nehmen `mod_env` als Fixture-Argument (statt `monkeypatch.setenv`). `mod_env` ist die tmp-Wurzel; `settings.modules_dir`==`mod_env/"modules"`, `settings.base_dir`==`mod_env/"repo"`, `settings.module_hub_cache`==`mod_env/"hub"`, DB==`mod_env/"test.db"`.

---

## Task 1: Settings — modules_dir + Hub-Pfade

> **Verifiziert:** Pfade leben in `settings/_paths.py` als `cached_property` + `os.environ.get` (NICHT `env_or_override`, NICHT eigener Mixin). `plugins_dir`/`plugin_hub_cache`/`plugin_hub_git_url` sind dort die direkte Vorlage (`_paths.py:36-48`). Repo-Root = `settings.base_dir` (`/opt/hydrahive2`, env `HH_BASE_DIR`, `_paths.py:16-17`).

**Files:** Modify `core/src/hydrahive/settings/_paths.py` (neben die plugin-Pfade) · Test `core/tests/test_modules_settings.py`

- [ ] **Step 1: Failing test** (Freeze umgehen: data_dir umbiegen + evtl. gecachten Wert löschen)
```python
# core/tests/test_modules_settings.py
def test_modules_dir_under_data_dir(monkeypatch, tmp_path):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path, raising=False)
    monkeypatch.delattr(settings, "modules_dir", raising=False)  # ggf. gecachten cached_property-Wert entfernen
    assert settings.modules_dir == tmp_path / "modules"

def test_module_hub_git_url_is_set():
    from hydrahive.settings import settings
    assert isinstance(settings.module_hub_git_url, str) and settings.module_hub_git_url
```
- [ ] **Step 2:** Run `pytest core/tests/test_modules_settings.py -v` → FAIL (`AttributeError: modules_dir`).
- [ ] **Step 3: Implement** — in `_paths.py` direkt nach `plugin_hub_git_url` einfügen (gleicher Stil, `cached_property`):
```python
    @cached_property
    def modules_dir(self) -> Path:
        return self.data_dir / "modules"

    @cached_property
    def module_hub_cache(self) -> Path:
        return self.data_dir / ".module-cache" / "hub"

    @cached_property
    def module_hub_git_url(self) -> str:
        return os.environ.get(
            "HH_MODULE_HUB_GIT_URL",
            "https://github.com/hydrahive/hydrahive2-modules.git",
        )
```
- [ ] **Step 4:** Run `pytest core/tests/test_modules_settings.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Settings-Pfade (modules_dir + Hub)"`.

---

## Task 2: Migration 027 + Per-Modul-Migrations-Runner

**Files:** Create `db/migrations/027_module_schema_version.sql`, `modules/migrations.py` · Test `core/tests/test_module_migrations.py`

- [ ] **Step 1: Migration schreiben**
```sql
-- core/src/hydrahive/db/migrations/027_module_schema_version.sql
CREATE TABLE IF NOT EXISTS module_schema_version (
    module_id   TEXT NOT NULL,
    version     INTEGER NOT NULL,
    applied_at  TEXT NOT NULL,
    PRIMARY KEY (module_id, version)
);
```
- [ ] **Step 2: Failing test** (nutzt `mod_env` aus Task 0 — frische DB inkl. 027)
```python
# core/tests/test_module_migrations.py
from hydrahive.db.connection import db

def test_apply_module_migrations_creates_and_tracks(mod_env):
    mdir = mod_env / "m"; mdir.mkdir()
    (mdir / "001_x.sql").write_text("CREATE TABLE module_x_t (id INTEGER);")
    from hydrahive.modules.migrations import apply_module_migrations
    apply_module_migrations("x", mdir)
    with db() as c:
        ver = c.execute("SELECT MAX(version) FROM module_schema_version WHERE module_id='x'").fetchone()[0]
        cols = [r[1] for r in c.execute("PRAGMA table_info(module_x_t)").fetchall()]
    assert ver == 1 and "id" in cols

def test_apply_module_migrations_idempotent_preserves_data(mod_env):
    mdir = mod_env / "m"; mdir.mkdir()
    (mdir / "001_y.sql").write_text("CREATE TABLE module_y_t (id INTEGER);")
    from hydrahive.modules.migrations import apply_module_migrations
    apply_module_migrations("y", mdir)
    with db() as c:
        c.execute("INSERT INTO module_y_t (id) VALUES (42)")
    apply_module_migrations("y", mdir)  # zweiter Lauf = Re-Install
    with db() as c:
        rows = c.execute("SELECT id FROM module_y_t").fetchall()
    assert rows == [(42,)]  # Daten überleben
```
- [ ] **Step 3:** Run `pytest core/tests/test_module_migrations.py -v` → FAIL (`ModuleNotFoundError`).
- [ ] **Step 4: Implement** `modules/migrations.py`:
```python
"""Per-Modul-Migrationen — eigene Versions-Tabelle, getrennt vom Core."""
from __future__ import annotations
import logging
import sqlite3
from pathlib import Path
from hydrahive.db.connection import db
from hydrahive.db._utils import now_iso  # VERIFIZIERT: gleiche Quelle wie db/migrations.py:7

logger = logging.getLogger(__name__)

def _current(conn, module_id: str) -> int:
    row = conn.execute(
        "SELECT MAX(version) FROM module_schema_version WHERE module_id = ?", (module_id,)
    ).fetchone()
    return (row[0] if row else 0) or 0

def apply_module_migrations(module_id: str, migrations_dir: Path) -> None:
    """Wendet ausstehende NNN_*.sql des Moduls an, trackt pro Modul.
    Deinstall ruft das NICHT rückwärts — Daten bleiben."""
    migrations_dir = Path(migrations_dir)
    if not migrations_dir.is_dir():
        return
    with db() as conn:
        current = _current(conn, module_id)
        for f in sorted(migrations_dir.glob("*.sql")):
            try:
                version = int(f.name.split("_", 1)[0])
            except ValueError:
                logger.warning("Modul %s: Migration %s ohne Versions-Prefix — übersprungen", module_id, f.name)
                continue
            if version <= current:
                continue
            try:
                conn.executescript(f.read_text())
            except sqlite3.OperationalError as exc:  # partiell angewendet (Muster db/migrations.py:47-52)
                if "duplicate column name" not in str(exc) and "already exists" not in str(exc):
                    raise
                logger.warning("Modul %s: Migration %s bereits partiell — markiere als erledigt (%s)", module_id, f.name, exc)
            conn.execute(
                "INSERT OR IGNORE INTO module_schema_version (module_id, version, applied_at) VALUES (?, ?, ?)",
                (module_id, version, now_iso()),
            )
            logger.info("Modul %s: Migration %s angewendet (v%d)", module_id, f.name, version)
```
- [ ] **Step 5:** Run `pytest core/tests/test_module_migrations.py -v` → PASS.
- [ ] **Step 6:** Commit: `git add -A && git commit -m "feat(modules): Migration 027 + per-Modul-Migrations-Runner"`.

---

## Task 3: ModuleManifest

**Files:** Create `modules/manifest.py` · Test `core/tests/test_module_manifest.py`

- [ ] **Step 1: Failing test**
```python
# core/tests/test_module_manifest.py
def test_parse_valid_manifest(tmp_path):
    import json
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id":"example","name":"Beispiel","version":"1.0.0"}))
    from hydrahive.modules.manifest import ModuleManifest
    m = ModuleManifest.load(p)
    assert m.id == "example" and m.version == "1.0.0" and m.has_service is False

def test_manifest_rejects_bad_id(tmp_path):
    import json, pytest
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id":"Bad Id!","name":"x","version":"1"}))
    from hydrahive.modules.manifest import ModuleManifest, ManifestError
    with pytest.raises(ManifestError):
        ModuleManifest.load(p)
```
- [ ] **Step 2:** Run `pytest core/tests/test_module_manifest.py -v` → FAIL.
- [ ] **Step 3: Implement** `modules/manifest.py`:
```python
from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

class ManifestError(Exception): ...

@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    icon: str = "Boxes"
    nav_group: str = "working"
    permissions: tuple[str, ...] = ()
    has_service: bool = False
    min_core_version: str = "2.0.0"

    @classmethod
    def load(cls, path: Path) -> "ModuleManifest":
        try:
            d = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise ManifestError(f"manifest.json nicht lesbar: {e}") from e
        for key in ("id", "name", "version"):
            if not d.get(key):
                raise ManifestError(f"manifest.json: Pflichtfeld '{key}' fehlt")
        if not _ID_RE.match(d["id"]):
            raise ManifestError(f"manifest.json: ungültige id {d['id']!r} (nur a-z0-9-)")
        return cls(
            id=d["id"], name=d["name"], version=str(d["version"]),
            icon=d.get("icon", "Boxes"), nav_group=d.get("nav_group", "working"),
            permissions=tuple(d.get("permissions", [])),
            has_service=bool(d.get("has_service", False)),
            min_core_version=d.get("min_core_version", "2.0.0"),
        )
```
- [ ] **Step 4:** Run `pytest core/tests/test_module_manifest.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): ModuleManifest"`.

---

## Task 4: ModuleContext + Registry + Fassade

**Files:** Create `modules/context.py`, `modules/registry.py`, `modules/__init__.py` · Test `core/tests/test_module_context.py`

- [ ] **Step 1: Failing test**
```python
# core/tests/test_module_context.py
def test_context_accumulates():
    from hydrahive.modules.context import ModuleContext
    from fastapi import APIRouter
    ctx = ModuleContext("example")
    r = APIRouter()
    ctx.register_router(r)
    ctx.register_migrations("migrations")
    ctx.register_service("extension")
    assert ctx.routers == [r]
    assert ctx.migrations_rel == "migrations"
    assert ctx.service_rel == "extension"
```
- [ ] **Step 2:** Run `pytest core/tests/test_module_context.py -v` → FAIL.
- [ ] **Step 3: Implement** `modules/context.py`:
```python
from __future__ import annotations
from fastapi import APIRouter

class ModuleContext:
    """Was ein Modul beim register() registrieren kann."""
    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.routers: list[APIRouter] = []
        self.migrations_rel: str | None = None
        self.service_rel: str | None = None

    def register_router(self, router: APIRouter) -> None:
        self.routers.append(router)

    def register_migrations(self, rel_dir: str) -> None:
        self.migrations_rel = rel_dir

    def register_service(self, rel_dir: str) -> None:
        self.service_rel = rel_dir
```
`modules/registry.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.context import ModuleContext

@dataclass
class LoadedModule:
    name: str
    manifest: ModuleManifest | None
    path: Path
    ctx: ModuleContext | None = None
    loaded: bool = False
    error: str | None = None

REGISTRY: dict[str, LoadedModule] = {}
```
`modules/__init__.py`:
```python
from hydrahive.modules.loader import load_all
from hydrahive.modules.registry import REGISTRY, LoadedModule
__all__ = ["load_all", "REGISTRY", "LoadedModule"]
```
> `__init__.py` importiert `loader` — Task 5 muss existieren bevor dieser Import lädt. Reihenfolge: erst context/registry committen, `__init__.py` erst nach Task 5 finalisieren (oder hier `load_all` lazy importieren). Pragmatisch: in diesem Task `__init__.py` ohne loader-Import lassen, in Task 5 ergänzen.
- [ ] **Step 4:** Run `pytest core/tests/test_module_context.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): ModuleContext + Registry"`.

---

## Task 5: Loader (load_all)

**Files:** Modify `modules/loader.py` (Create), `modules/__init__.py` · Test `core/tests/test_module_loader.py`

- [ ] **Step 1: Failing test** (Fake-Modul-Dir, echte DB)
```python
# core/tests/test_module_loader.py — lazy imports
def _make_module(modules_dir, mid):
    md = modules_dir / mid; (md / "backend").mkdir(parents=True); (md / "migrations").mkdir()
    (md / "manifest.json").write_text('{"id":"%s","name":"X","version":"1.0.0"}' % mid)
    (md / "migrations" / "001_t.sql").write_text(f"CREATE TABLE module_{mid}_t (id INTEGER);")
    (md / "backend" / "__init__.py").write_text(
        "from fastapi import APIRouter\n"
        "def register(ctx):\n"
        "    r=APIRouter()\n"
        "    @r.get('/ping')\n"
        "    def ping(): return {'ok': True}\n"
        "    ctx.register_router(r)\n"
        "    ctx.register_migrations('migrations')\n")
    return md

def test_load_all_loads_module_and_migrations(mod_env):
    from hydrahive.db.connection import db
    _make_module(mod_env / "modules", "alpha")   # == settings.modules_dir
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    assert REGISTRY["alpha"].loaded is True
    assert REGISTRY["alpha"].ctx.routers
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_schema_version WHERE module_id='alpha'").fetchone()[0] == 1

def test_load_all_isolates_broken_module(mod_env):
    _make_module(mod_env / "modules", "good")
    bad = mod_env / "modules" / "bad"; (bad / "backend").mkdir(parents=True)
    (bad / "manifest.json").write_text('{"id":"bad","name":"B","version":"1"}')
    (bad / "backend" / "__init__.py").write_text("raise RuntimeError('boom')\n")
    from hydrahive.modules.loader import load_all
    from hydrahive.modules.registry import REGISTRY
    load_all()
    assert REGISTRY["good"].loaded is True
    assert REGISTRY["bad"].loaded is False and REGISTRY["bad"].error
```
- [ ] **Step 2:** Run `pytest core/tests/test_module_loader.py -v` → FAIL.
- [ ] **Step 3: Implement** `modules/loader.py` (Muster `plugins/loader.py:43-124`):
```python
from __future__ import annotations
import importlib.util, logging, sys
from pathlib import Path
from hydrahive.modules.manifest import ModuleManifest, ManifestError
from hydrahive.modules.context import ModuleContext
from hydrahive.modules.registry import REGISTRY, LoadedModule
from hydrahive.modules.migrations import apply_module_migrations

logger = logging.getLogger(__name__)

def _import_backend(module_dir: Path, mid: str):
    safe = "hhmod_" + mid.replace("-", "_")
    backend = module_dir / "backend"
    parent = str(backend.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(
        safe, backend / "__init__.py", submodule_search_locations=[str(backend)])
    if spec is None or spec.loader is None:
        raise ImportError(f"Spec für {backend} nicht erzeugbar")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[safe] = mod
    spec.loader.exec_module(mod)
    return mod

def _load_one(module_dir: Path) -> LoadedModule:
    name = module_dir.name
    try:
        manifest = ModuleManifest.load(module_dir / "manifest.json")
    except ManifestError as e:
        return LoadedModule(name=name, manifest=None, path=module_dir, error=str(e))
    try:
        backend = _import_backend(module_dir, manifest.id)
        register = getattr(backend, "register", None)
        if not callable(register):
            return LoadedModule(name=name, manifest=manifest, path=module_dir,
                                error="backend/__init__.py hat kein register(ctx)")
        ctx = ModuleContext(manifest.id)
        register(ctx)
        if ctx.migrations_rel:
            apply_module_migrations(manifest.id, module_dir / ctx.migrations_rel)
    except Exception as e:  # Isolation: ein kaputtes Modul blockiert die anderen nicht
        logger.exception("Modul '%s' Laden fehlgeschlagen", name)
        return LoadedModule(name=name, manifest=manifest, path=module_dir, error=str(e))
    return LoadedModule(name=name, manifest=manifest, path=module_dir, ctx=ctx, loaded=True)

def load_all() -> None:
    from hydrahive.settings import settings  # lazy: data_dir-Freeze
    REGISTRY.clear()
    base = settings.modules_dir
    if not base.is_dir():
        return
    for module_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        loaded = _load_one(module_dir)
        REGISTRY[loaded.name] = loaded
        if loaded.loaded:
            logger.info("Modul '%s' geladen (v%s)", loaded.name, loaded.manifest.version)
        else:
            logger.warning("Modul '%s' nicht geladen: %s", loaded.name, loaded.error)
```
Dann `modules/__init__.py` finalisieren (loader-Import wie in Task 4 Step 3 gezeigt).
- [ ] **Step 4:** Run `pytest core/tests/test_module_loader.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Loader (load_all, importlib, Isolation, Migrationen)"`.

---

## Task 6: Backend-Verdrahtung in main.py

**Files:** Modify `core/src/hydrahive/api/main.py` · Test `core/tests/test_modules_main_wiring.py`

> **Wichtig:** `load_all()` läuft auf Modul-Ebene in `main.py` **einmal beim Import** → ein Test gegen die globale `app` ist timing-fragil (main ist via `client`-Fixture evtl. schon importiert). Daher die Verkabelung in eine **testbare Funktion** `mount_module_routers(app)` ausklammern und gegen eine Wegwerf-`FastAPI()` testen.

- [ ] **Step 1: Failing test** (Fake-Modul + Wegwerf-App)
```python
# core/tests/test_modules_main_wiring.py
def test_mount_module_routers(mod_env):
    from test_module_loader import _make_module   # gleicher Helfer wie Task 5
    _make_module(mod_env / "modules", "alpha")
    from fastapi import FastAPI
    from hydrahive.modules.loader import load_all
    from hydrahive.api.main import mount_module_routers
    load_all()
    test_app = FastAPI()
    mount_module_routers(test_app)
    paths = {r.path for r in test_app.routes if hasattr(r, "path")}
    assert "/api/modules/alpha/ping" in paths
```
- [ ] **Step 2:** Run `pytest core/tests/test_modules_main_wiring.py -v` → FAIL (`ImportError: mount_module_routers`).
- [ ] **Step 3: Implement** in `api/main.py` — Helfer + Aufruf beim App-Aufbau (nach den bestehenden `include_router`-Zeilen):
```python
from hydrahive import modules as _modules

def mount_module_routers(target_app) -> None:
    for entry in _modules.REGISTRY.values():
        if entry.loaded and entry.ctx:
            for r in entry.ctx.routers:
                target_app.include_router(r, prefix=f"/api/modules/{entry.manifest.id}")

_modules.load_all()
mount_module_routers(app)
```
> Das Fake-Modul aus Task 5 registriert `r.get('/ping')`; `mount_module_routers` setzt `prefix=f"/api/modules/{id}"` → Pfad `/api/modules/alpha/ping`.
- [ ] **Step 4:** Run `pytest core/tests/test_modules_main_wiring.py -v` → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): load_all + Modul-Router in main.py einhängen"`.

---

## Task 7: Hub-Client

**Files:** Create `modules/hub_client.py` · Test `core/tests/test_module_hub.py` (git gemockt)

- [ ] **Step 1: Failing test**
```python
# core/tests/test_module_hub.py
def test_read_hub_index(mod_env):
    from hydrahive.settings import settings
    cache = settings.module_hub_cache; cache.mkdir(parents=True)  # mod_env/"hub" (per Fixture)
    (cache / "hub.json").write_text('{"modules":[{"id":"example","path":"example"}]}')
    from unittest.mock import patch
    with patch("hydrahive.modules.hub_client.refresh"):  # kein echtes git
        from hydrahive.modules.hub_client import read_hub_index
        idx = read_hub_index()
    assert idx["modules"][0]["id"] == "example"
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement** `modules/hub_client.py` (Adaption von `plugins/hub_client.py`, `module_*`-Settings, `module_source_path` mit Path-Escape-Schutz):
```python
"""Modul-Hub-Client: spiegelt das Hub-Repo als lokalen Cache (Muster plugins/hub_client.py)."""
from __future__ import annotations
import json, logging, subprocess
from pathlib import Path
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
_GIT_TIMEOUT = 60

class HubError(RuntimeError): ...

def _run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=_GIT_TIMEOUT, check=False)

def refresh() -> None:
    cache = settings.module_hub_cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    if (cache / ".git").exists():
        r = _run_git(["pull", "--ff-only"], cwd=cache)
        if r.returncode != 0:
            raise HubError(f"git pull failed: {r.stderr.strip()}")
        return
    if cache.exists():
        import shutil; shutil.rmtree(cache)
    r = _run_git(["clone", "--depth=1", "--filter=blob:none", settings.module_hub_git_url, str(cache)])
    if r.returncode != 0:
        raise HubError(f"git clone failed: {r.stderr.strip()}")

def read_hub_index() -> dict:
    cache = settings.module_hub_cache
    if not (cache / "hub.json").exists():
        refresh()
    try:
        return json.loads((cache / "hub.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HubError(f"hub.json nicht lesbar: {e}") from e

def module_source_path(module_path: str) -> Path:
    cache = settings.module_hub_cache
    full = (cache / module_path).resolve()
    if not str(full).startswith(str(cache.resolve())):  # kein Path-Escape ausm Cache
        raise HubError(f"ungültiger module-path: {module_path}")
    return full
```
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Hub-Client (git-Cache, hub.json)"`.

---

## Task 8: Installer — Backend-Dateioperationen (ohne Build/Restart)

**Files:** Create `modules/installer.py` · Test `core/tests/test_module_installer.py`

> **Verifiziert:** Frontend-Wurzel = `settings.base_dir / "frontend"` (`base_dir`=`/opt/hydrahive2`). Quelle wird über den Hub-Index aufgelöst (`_cache_path_for`, Muster `plugins/installer.py:35-42` mit `index.get("modules")` + `id`/`path`). v1-Konvention: `path` default == `id`.

- [ ] **Step 1: Failing test** (Kopieren rein, Uninstall lässt Daten)
```python
# core/tests/test_module_installer.py
def test_install_copies_backend_and_frontend(mod_env):
    from hydrahive.settings import settings
    src = settings.module_hub_cache / "example"     # Hub-Cache-Quelle (mod_env/"hub"/example)
    (src / "backend").mkdir(parents=True); (src / "frontend").mkdir(parents=True)
    (src / "manifest.json").write_text('{"id":"example","name":"X","version":"1.0.0"}')
    (src / "backend" / "__init__.py").write_text("def register(ctx): pass\n")
    (src / "frontend" / "index.tsx").write_text("export const routes=[]\n")
    (settings.base_dir / "frontend" / "src" / "modules").mkdir(parents=True)
    from unittest.mock import patch
    with (patch("hydrahive.modules.installer.refresh"),
          patch("hydrahive.modules.installer._cache_path_for", return_value=src)):
        from hydrahive.modules.installer import copy_module_in
        copy_module_in("example")
    assert (settings.modules_dir / "example" / "backend" / "__init__.py").exists()
    assert (settings.base_dir / "frontend" / "src" / "modules" / "example" / "index.tsx").exists()

def test_remove_module_keeps_no_data_touch(mod_env):
    from hydrahive.settings import settings
    md = settings.modules_dir / "example"; md.mkdir(parents=True); (md / "x").write_text("y")
    fe = settings.base_dir / "frontend" / "src" / "modules" / "example"; fe.mkdir(parents=True); (fe / "i").write_text("z")
    from hydrahive.modules.installer import remove_module_files
    remove_module_files("example")
    assert not md.exists() and not fe.exists()
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement** `modules/installer.py` (Datei-Teil; Muster `plugins/installer.py:35-96`):
```python
from __future__ import annotations
import shutil
from pathlib import Path
from hydrahive.modules import hub_client
from hydrahive.modules.hub_client import refresh
from hydrahive.settings import settings

class InstallError(RuntimeError): ...

def _frontend_modules_dir() -> Path:
    return settings.base_dir / "frontend" / "src" / "modules"   # VERIFIZIERT: base_dir=/opt/hydrahive2

def _cache_path_for(module_id: str) -> Path:
    index = hub_client.read_hub_index()
    for entry in index.get("modules", []):
        if entry.get("id") == module_id:
            return hub_client.module_source_path(entry.get("path") or module_id)
    raise InstallError(f"module_not_in_hub:{module_id}")

def copy_module_in(module_id: str) -> None:
    refresh()
    src = _cache_path_for(module_id)
    backend_dst = settings.modules_dir / module_id
    backend_dst.parent.mkdir(parents=True, exist_ok=True)
    if backend_dst.exists():
        shutil.rmtree(backend_dst)
    shutil.copytree(src, backend_dst, symlinks=False)            # backend+migrations+manifest(+frontend)
    fe_dst = _frontend_modules_dir() / module_id
    fe_dst.parent.mkdir(parents=True, exist_ok=True)
    if fe_dst.exists():
        shutil.rmtree(fe_dst)
    shutil.copytree(src / "frontend", fe_dst, symlinks=False)

def remove_module_files(module_id: str) -> None:
    for d in (settings.modules_dir / module_id, _frontend_modules_dir() / module_id):
        if d.exists():
            shutil.rmtree(d)
    # DB-Tabellen/Daten + module_schema_version bleiben unangetastet.
```
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Installer-Dateioperationen (copy in / remove, Daten bleiben)"`.

---

## Task 9: Frontend-Codegen (node prebuild) + gitignore

**Files:** Create `frontend/scripts/gen-modules.mjs` · Modify `frontend/package.json` (`prebuild`), `frontend/.gitignore` (oder root `.gitignore`) · Test: Codegen gegen Fixture laufen lassen

- [ ] **Step 1: Codegen schreiben** `frontend/scripts/gen-modules.mjs`:
```js
import { readdirSync, statSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const modulesDir = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "modules")
const out = join(modulesDir, "index.generated.ts")

const ids = existsSync(modulesDir)
  ? readdirSync(modulesDir).filter((n) => {
      const p = join(modulesDir, n)
      return statSync(p).isDirectory() && existsSync(join(p, "index.tsx"))
    })
  : []

const imports = ids.map((id, i) => `import * as m${i} from "./${id}"`).join("\n")
const routes = ids.map((_, i) => `...m${i}.routes`).join(", ")
const nav = ids.map((_, i) => `...m${i}.nav`).join(", ")
const i18n = ids.map((_, i) => `m${i}.i18n`).join(", ")
writeFileSync(out,
`// AUTO-GENERATED by scripts/gen-modules.mjs — do not edit.
${imports}
export const moduleRoutes = [${routes}]
export const moduleNav = [${nav}]
export const moduleI18n = [${i18n}]
`)
console.log(`[gen-modules] ${ids.length} Modul(e): ${ids.join(", ") || "(keine)"}`)
```
- [ ] **Step 2:** `frontend/package.json` `scripts`: `"prebuild": "node scripts/gen-modules.mjs"` ergänzen (npm ruft `prebuild` automatisch vor `build`). `.gitignore`: `frontend/src/modules/*/` und `frontend/src/modules/index.generated.ts` eintragen (Modul-Code + generierte Datei nicht committen).
- [ ] **Step 3: Test (Fixture)** — leeres modules-Dir → leere Registry:
```bash
cd frontend && node scripts/gen-modules.mjs && cat src/modules/index.generated.ts
# Erwartung: moduleRoutes = [] etc. (keine Module)
```
Dann ein Fixture-Modul anlegen + erneut:
```bash
mkdir -p src/modules/example && echo 'export const routes=[];export const nav=[];export const i18n={}' > src/modules/example/index.tsx
node scripts/gen-modules.mjs && grep -q 'import \* as m0 from "./example"' src/modules/index.generated.ts && echo OK
rm -rf src/modules/example src/modules/index.generated.ts
```
Erwartung: `OK`.
- [ ] **Step 4:** `npm run build` → muss grün sein (prebuild erzeugt leere Registry, App importiert sie — nach Task 10).
- [ ] **Step 5:** Commit: `git add frontend/scripts/gen-modules.mjs frontend/package.json .gitignore && git commit -m "feat(modules): Frontend-Codegen (gen-modules prebuild) + gitignore"`.

---

## Task 10: Core-Frontend-Hooks (App/Nav/i18n + Icon-Resolver)

**Files:** Create `frontend/src/shared/module-icon.ts` · Modify `frontend/src/App.tsx`, `frontend/src/shared/nav-config.ts`, `frontend/src/i18n/index.ts`

- [ ] **Step 1: Icon-Resolver** `frontend/src/shared/module-icon.ts`:
```ts
import * as Icons from "lucide-react"
import type { ComponentType } from "react"
export function moduleIcon(name: string): ComponentType<{ size?: number }> {
  return (Icons as Record<string, ComponentType<{ size?: number }>>)[name] ?? Icons.Boxes
}
```
- [ ] **Step 2: App.tsx** — Import + Modul-Routen in den geschützten Block:
```tsx
import { moduleRoutes } from "@/modules/index.generated"
// ... innerhalb der <Route path="/" element={<Guard><Layout/></Guard>}> Kinder:
{moduleRoutes.map((r) => (
  <Route key={r.path} path={r.path.replace(/^\//, "")} element={r.element} />
))}
```
- [ ] **Step 3: nav-config.ts** — Modul-Nav mergen:
```ts
import { moduleNav } from "@/modules/index.generated"
import { moduleIcon } from "@/shared/module-icon"
// nach NAV_ITEMS-Definition:
export const MODULE_NAV_ITEMS: NavItem[] = moduleNav.map((n) => ({
  path: n.path, icon: moduleIcon(n.icon), labelKey: n.labelKey, group: n.group, roles: n.roles,
}))
// visibleItems erweitern: [...NAV_ITEMS, ...MODULE_NAV_ITEMS].filter(...)
```
> Passe `visibleItems()` an, dass es `[...NAV_ITEMS, ...MODULE_NAV_ITEMS]` filtert.
- [ ] **Step 4: i18n/index.ts** — Modul-Bundles mergen:
```ts
import { moduleI18n } from "@/modules/index.generated"
// vor i18n.init: moduleI18n in resources.de/.en mergen:
for (const bundle of moduleI18n) {
  for (const lng of ["de", "en"] as const) {
    Object.assign((resources as any)[lng], bundle[lng] ?? {})
  }
}
```
> `@/modules/index.generated` muss existieren — `npm run build` erzeugt sie via prebuild; für `tsc`-Dev sicherstellen, dass die Datei da ist (einmal `node scripts/gen-modules.mjs` laufen lassen). Alias `@/modules` → `src/modules` in `tsconfig`/`vite.config` prüfen (vermutlich `@/*`→`src/*` schon vorhanden).
- [ ] **Step 5:** `cd frontend && node scripts/gen-modules.mjs && npm run build` → grün.
- [ ] **Step 6:** Commit: `git add -A && git commit -m "feat(modules): Core-Frontend-Hooks (App/Nav/i18n + Icon-Resolver)"`.

---

## Task 11: Install/Deinstall-Orchestrierung (Build + Restart + Dienst)

**Files:** Modify `modules/installer.py` (orchestrierende Funktionen) · Test `core/tests/test_module_install_flow.py` (Build/Restart/Service gemockt)

- [ ] **Step 1: Failing test**
```python
# core/tests/test_module_install_flow.py
def test_install_flow_calls_steps(mod_env):
    from unittest.mock import patch
    with (patch("hydrahive.modules.installer.copy_module_in") as cp,
          patch("hydrahive.modules.installer._run_service_script") as svc,
          patch("hydrahive.modules.installer._frontend_build") as build,
          patch("hydrahive.modules.installer._request_restart") as restart,
          patch("hydrahive.modules.installer._manifest_has_service", return_value=False)):
        from hydrahive.modules.installer import install
        list(install("example"))   # Generator (Log-Zeilen)
    cp.assert_called_once_with("example")
    build.assert_called_once()
    restart.assert_called_once()
    svc.assert_not_called()

def test_uninstall_keeps_data(mod_env):
    from unittest.mock import patch
    with (patch("hydrahive.modules.installer.remove_module_files") as rm,
          patch("hydrahive.modules.installer._run_service_script") as svc,
          patch("hydrahive.modules.installer._frontend_build"),
          patch("hydrahive.modules.installer._request_restart"),
          patch("hydrahive.modules.installer._manifest_has_service", return_value=False)):
        from hydrahive.modules.installer import uninstall
        list(uninstall("example"))
    rm.assert_called_once_with("example")
    # KEIN drop-table-Aufruf existiert — Daten bleiben per Design.
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement** in `modules/installer.py` (Generatoren, die Log-Zeilen yielden — für SSE; `import subprocess` oben ergänzen, `settings` ist schon importiert):
```python
# import subprocess  ← oben zu den Imports
def _frontend_build():
    fe = settings.base_dir / "frontend"   # VERIFIZIERT: base_dir=/opt/hydrahive2
    subprocess.run(["npm", "run", "build"], cwd=fe, check=True)

def _request_restart():
    (settings.data_dir / ".restart_request").write_text("module-change")  # VERIFIZIERT: system_admin.py:29

def _manifest_has_service(module_id: str) -> bool:
    from hydrahive.modules.manifest import ModuleManifest
    return ModuleManifest.load(settings.modules_dir / module_id / "manifest.json").has_service

def _run_service_script(module_id: str, script: str):  # "install.sh" | "uninstall.sh"
    path = settings.modules_dir / module_id / "extension" / script
    if path.exists():
        subprocess.run(["bash", str(path)], check=True)

def install(module_id: str):
    yield f"[modules] installiere {module_id} …"
    copy_module_in(module_id); yield "[modules] Dateien kopiert"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "install.sh"); yield "[modules] Dienst installiert"
    _frontend_build(); yield "[modules] Frontend gebaut"
    _request_restart(); yield "[modules] Neustart angefordert — fertig"

def uninstall(module_id: str):
    yield f"[modules] deinstalliere {module_id} …"
    if _manifest_has_service(module_id):
        _run_service_script(module_id, "uninstall.sh"); yield "[modules] Dienst entfernt"
    remove_module_files(module_id); yield "[modules] Dateien entfernt (Daten bleiben)"
    _frontend_build(); yield "[modules] Frontend gebaut"
    _request_restart(); yield "[modules] Neustart angefordert — fertig"
```
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Install/Deinstall-Orchestrierung (Build + Restart + Dienst)"`.

---

## Task 12: Admin-API-Routen

> **Verifiziert + Design-Entscheidung:** Admin-Router unter Prefix **`/api/admin/modules`** (exakt wie `extensions.py:30` `/api/admin/extensions`). Das vermeidet **jede** Kollision mit den per-Modul-Routern aus Task 6 (`/api/modules/{id}/…`) — getrennte Namespaces, keine Reihenfolge-Abhängigkeit. SSE-Format **verifiziert** aus `extensions.py:98/120/121`: `data: {json.dumps({'line': line})}\n\n` je Zeile, `data: {"done": true}\n\n` am Ende, `media_type="text/event-stream"`, `headers=_SSE_HEADERS`.

**Files:** Create `core/src/hydrahive/api/routes/modules.py` · Modify `api/main.py` (Router registrieren) · Test `core/tests/test_modules_routes.py`

- [ ] **Step 1: Failing test**
```python
# core/tests/test_modules_routes.py — TestClient, require_admin override
def test_list_modules_admin(monkeypatch, setup_test_env):
    from fastapi.testclient import TestClient
    from hydrahive.api.main import app
    from hydrahive.api.middleware.auth import require_admin
    app.dependency_overrides[require_admin] = lambda: ("admin", "admin")
    try:
        with TestClient(app) as c:
            r = c.get("/api/admin/modules")
        assert r.status_code == 200 and "installed" in r.json()
    finally:
        app.dependency_overrides.pop(require_admin, None)

def test_install_streams(monkeypatch, setup_test_env):
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from hydrahive.api.main import app
    from hydrahive.api.middleware.auth import require_admin
    app.dependency_overrides[require_admin] = lambda: ("admin", "admin")
    try:
        with patch("hydrahive.api.routes.modules.installer.install", return_value=iter(["line1", "done"])):
            with TestClient(app) as c:
                r = c.post("/api/admin/modules/example/install")
        assert r.status_code == 200 and "line1" in r.text
    finally:
        app.dependency_overrides.pop(require_admin, None)
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement** `routes/modules.py` (SSE-Helfer 1:1 wie `extensions.py`):
```python
from __future__ import annotations
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from hydrahive.api.middleware.auth import require_admin
from hydrahive.modules import REGISTRY, installer, hub_client

router = APIRouter(prefix="/api/admin/modules", tags=["modules"])
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

@router.get("", dependencies=[Depends(require_admin)])
def list_modules() -> dict:
    installed = [{"id": m.name, "loaded": m.loaded, "error": m.error,
                  "version": m.manifest.version if m.manifest else None}
                 for m in REGISTRY.values()]
    try:
        available = hub_client.read_hub_index().get("modules", [])
    except Exception:
        available = []
    return {"installed": installed, "available": available}

def _stream(gen) -> StreamingResponse:
    def _events():
        for line in gen:
            yield f"data: {json.dumps({'line': line})}\n\n"
        yield "data: {\"done\": true}\n\n"
    return StreamingResponse(_events(), media_type="text/event-stream", headers=_SSE_HEADERS)

@router.post("/{module_id}/install", dependencies=[Depends(require_admin)])
def install_module(module_id: str) -> StreamingResponse:
    return _stream(installer.install(module_id))

@router.delete("/{module_id}", dependencies=[Depends(require_admin)])
def uninstall_module(module_id: str) -> StreamingResponse:
    return _stream(installer.uninstall(module_id))
```
`api/main.py`: `from hydrahive.api.routes.modules import router as modules_admin_router` + `app.include_router(modules_admin_router)` (zu den anderen `include_router`-Zeilen, vor dem `load_all`-Block aus Task 6 — Reihenfolge unkritisch, da getrennte Namespaces).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Admin-API (list/install/uninstall, streamed)"`.

---

## Task 13: Admin-UI (Modules-Seite)

**Files:** Create `frontend/src/features/modules/{api.ts,types.ts,ModulesPage.tsx,ModuleCard.tsx}` · Modify `App.tsx` (Route), `nav-config.ts` (NavItem admin-only), `colors.ts`, `i18n` (Namespace `modules`)

- [ ] **Step 1:** `features/modules/types.ts` + `features/modules/api.ts`. `BASE = "/admin/modules"` (Endpoint = `/api${BASE}/…`, verifiziert gegen Task 12). SSE-Reader 1:1 nach `features/extensions/api.ts:16-59`, aber mit `method`-Param (install=POST, uninstall=DELETE):
```ts
// types.ts
export interface InstalledModule { id: string; loaded: boolean; error: string | null; version: string | null }
export interface AvailableModule { id: string; name?: string; path?: string }
export interface ModulesIndex { installed: InstalledModule[]; available: AvailableModule[] }
```
```ts
// api.ts
import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { ModulesIndex } from "./types"

const BASE = "/admin/modules"
const authHeaders = (): Record<string, string> => {
  const t = useAuthStore.getState().token
  return t ? { Authorization: `Bearer ${t}` } : {}
}
export const listModules = () => api.get<ModulesIndex>(BASE)

function stream(path: string, method: "POST" | "DELETE",
                onLine: (l: string) => void, onDone: () => void, onError: (m: string) => void): () => void {
  let closed = false
  const ctrl = new AbortController()
  fetch(`/api${BASE}${path}`, { method, headers: authHeaders(), signal: ctrl.signal })
    .then(async (r) => {
      if (!r.ok || !r.body) { onError(`HTTP ${r.status}`); return }
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done || closed) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split("\n\n"); buf = parts.pop() ?? ""
        for (const part of parts) {
          const dl = part.split("\n").find((l) => l.startsWith("data:"))
          if (!dl) continue
          try {
            const obj = JSON.parse(dl.slice(5).trim())
            if (obj.done) { onDone(); return }
            if (obj.line !== undefined) onLine(obj.line)
          } catch { /* keepalive */ }
        }
      }
    }).catch((e) => { if (!closed) onError(String(e)) })
  return () => { closed = true; ctrl.abort() }
}
export const installModule = (id: string, onLine: (l: string) => void, onDone: () => void, onError: (m: string) => void) =>
  stream(`/${id}/install`, "POST", onLine, onDone, onError)
export const uninstallModule = (id: string, onLine: (l: string) => void, onDone: () => void, onError: (m: string) => void) =>
  stream(`/${id}`, "DELETE", onLine, onDone, onError)
```
- [ ] **Step 2:** `ModuleCard.tsx` (Name/Version/Status + Install- bzw. Deinstall-Button + Log-`<pre>`, Zeilen aus `onLine` sammeln) und `ModulesPage.tsx` (lädt `listModules()`, rendert installierte + im Hub verfügbare Module als Cards). Layout/Verhalten 1:1 nach `features/extensions/ExtensionsPage.tsx` + `ExtensionCard.tsx` (gleiche Lade-/Streaming-/Fehler-Logik, nur `installModule`/`uninstallModule` statt `streamAction`).
- [ ] **Step 3: Verkabelung:** `App.tsx` `<Route path="modules" element={<ModulesPage/>}/>` (im geschützten Block); `nav-config.ts` NavItem `{path:"/modules", icon: Boxes, labelKey:"nav.modules", group:"settings", roles:["admin"]}`; Farb-/Icon-Map analog Extensions; i18n-Namespace `modules` de+en (`locales/{de,en}/modules.json` + im i18n-index registrieren — Muster wie Extensions-Locale). **Hinweis:** das ist der *Admin-UI*-Eintrag (fix im Core), unabhängig vom per-Modul-Nav aus Task 10.
- [ ] **Step 4:** `cd frontend && node scripts/gen-modules.mjs && npm run build` → grün; `npx eslint src/features/modules` → grün.
- [ ] **Step 5:** Commit: `git add -A && git commit -m "feat(modules): Admin-UI (Modules-Seite, install/uninstall)"`.

---

## Task 14: Template-Modul `example`

**Files:** Create `modules/example/{manifest.json,backend/__init__.py,migrations/001_example.sql,frontend/index.tsx,frontend/ExamplePage.tsx}` + Hub-Index-Eintrag

- [ ] **Step 1:** `modules/example/manifest.json`:
```json
{ "id": "example", "name": "Beispiel-Modul", "version": "1.0.0", "icon": "Boxes",
  "nav_group": "working", "permissions": [], "has_service": false, "min_core_version": "2.0.0" }
```
- [ ] **Step 2:** `modules/example/migrations/001_example.sql`:
```sql
CREATE TABLE IF NOT EXISTS module_example_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
```
- [ ] **Step 3:** `modules/example/backend/__init__.py`:
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from hydrahive.api.middleware.auth import require_auth
from hydrahive.db.connection import db

router = APIRouter()

class NoteIn(BaseModel):
    text: str

@router.get("/notes", dependencies=[Depends(require_auth)])
def list_notes() -> list[dict]:
    with db() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, text, created_at FROM module_example_notes ORDER BY id DESC").fetchall()]

@router.post("/notes", dependencies=[Depends(require_auth)])
def add_note(body: NoteIn) -> dict:
    with db() as c:
        cur = c.execute("INSERT INTO module_example_notes (text) VALUES (?)", (body.text,))
        return {"id": cur.lastrowid, "text": body.text}

def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
```
- [ ] **Step 4:** `modules/example/frontend/index.tsx` (+ `ExamplePage.tsx`):
```tsx
import { ExamplePage } from "./ExamplePage"
export const routes = [{ path: "/example", element: <ExamplePage /> }]
export const nav = [{ path: "/example", icon: "Boxes", labelKey: "example", group: "working", roles: [] }]
export const i18n = { de: { example: { title: "Beispiel-Modul", add: "Hinzufügen" } },
                      en: { example: { title: "Example module", add: "Add" } } }
```
`ExamplePage.tsx`: lädt `GET /api/modules/example/notes`, Eingabe → `POST` → Liste (nutzt `@/shared/api-client`). (Vollständige, einfache Liste+Input-Komponente; keine externe Abhängigkeit.)
- [ ] **Step 5:** Hub-Index-Eintrag (für lokalen Test): im Modul-Hub-Repo `hub.json` `{"modules":[{"id":"example","path":"example"}]}`; das `example/`-Dir liegt parallel. (Für den `.23`-Test reicht ein lokaler Hub mit diesem einen Modul.)
- [ ] **Step 6:** Commit: `git add modules/example && git commit -m "feat(modules): Template-Modul example (Walking Skeleton)"`.

---

## Task 15: Integration — Build, Suite, Live-E2E

- [ ] **Step 1:** Volle Backend-Suite: `pytest core/tests/ -q -k "module"` → alle grün.
- [ ] **Step 2:** `cd frontend && node scripts/gen-modules.mjs && npm run build` → grün; `npx eslint src/features/modules src/shared/module-icon.ts` → grün.
- [ ] **Step 3:** Doppel-Review (code-reviewer + security-reviewer) auf den modules-Diff — Schwerpunkt: Loader-Isolation, Pfad-Sicherheit (module_id in Pfaden → traversal?), `subprocess`-Aufrufe (build/bash), Admin-Authz, Daten-bleiben-bei-Deinstall.
- [ ] **Step 4: Live-E2E auf `.23`** (Till + Claude): lokalen Modul-Hub mit `example` bereitstellen → über die Modules-Seite **installieren** → „Beispiel" erscheint im Nav, Seite liest/schreibt Notes → **deinstallieren** → weg → **re-install** → Notes wieder da. Finaler Beweis.
- [ ] **Step 5:** Spec-Abgleich + Feature-Map/ROADMAP nachziehen (neues Subsystem = Map-Sektion + ROADMAP-Update).

---

## Verifizierte Fakten (im Plan eingearbeitet — nicht mehr offen)
- Repo-Root = `settings.base_dir` (`/opt/hydrahive2`, `_paths.py:16-17`) → `_frontend_modules_dir`/`_frontend_build` nutzen das.
- `now_iso` = `from hydrahive.db._utils import now_iso` (`db/migrations.py:7`).
- Restart-Trigger = `settings.data_dir / ".restart_request"` (`system_admin.py:29`).
- Auth = `require_auth` / `require_admin` aus `hydrahive.api.middleware.auth` (`auth.py:36/53`).
- SSE-Format = `data: {json.dumps({'line': line})}\n\n` + `data: {"done": true}\n\n`, `_SSE_HEADERS`, `text/event-stream` (`extensions.py:98/120/121`); Frontend-Reader liest `obj.line`/`obj.done` (`extensions/api.ts:42-58`).
- Admin-Router-Namespace `/api/admin/modules` (≠ per-Modul `/api/modules/{id}`) → keine Routen-Kollision.

## Beim Bau noch zu prüfen (kein Blocker)
- Vite-/tsconfig-Alias `@/modules` → `src/modules` (vermutlich via `@/*`→`src/*` schon abgedeckt — in `vite.config.ts`/`tsconfig.json` bestätigen, sonst Alias ergänzen).
- SSE-Restart-Timing: `.restart_request` startet das Backend mitten in der Streaming-Response neu → der Client sieht das abschließende `done`-Event evtl. nicht. Frontend muss den Verbindungsabbruch am Ende tolerieren (wie Extensions: `onError`/Abbruch nach letzter Log-Zeile nicht als Fehler werten).
- `register_service` ist im `ModuleContext`-Vertrag (Task 4) vorhanden, wird in v1 aber nur über `has_service`+`extension/`-Scripts genutzt (Task 11); `ctx.service_rel` selbst bleibt v1 ungenutzt (echter Dienst-Proof erst bei Team-Chat-Migration, Sub-Projekt 3).
