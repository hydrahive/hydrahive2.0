# Modulsystem v1

> Dritte Extensibility-Stufe von HydraHive2: **Voll-Stack-Module** — eigenes Git-Repo,
> per Knopf installier-/deinstallierbar, bringen UI + API + Migrationen + optionalen
> Dienst in einem Stück. Install/Deinstall löst Frontend-Rebuild + Backend-Restart aus.
> **Modul-Daten bleiben bei Deinstall erhalten** (Re-Install stellt Tabellen + Daten wieder her).
>
> Architektur-Antwort auf das HH1-Monolith-Trauma: der Core wird für Module **einmalig**
> verdrahtet (drei statische Hooks), dann nie wieder pro Modul angefasst.
>
> Design-Dok: `docs/superpowers/specs/2026-06-04-modulsystem-v1-design.md` ·
> Plan: `docs/superpowers/plans/2026-06-04-modulsystem-v1.md`.
> Status (2026-06-04): **v1 komplett auf `main`**, Template-Modul `example` als Walking-Skeleton.

---

## WAS  (jede Fähigkeit / Modul / Endpoint / UI-Komponente einzeln)

### Drei Extensibility-Stufen

| Stufe | Verzeichnis | Inhalt |
|-------|-------------|--------|
| **Plugin** | `plugins/` | nur Agent-Tools (bestehend, unverändert) |
| **Extension** | `extensions/` | nur Dienste (install/uninstall-Scripts, z.B. tuwunel) |
| **Modul** | `<data_dir>/modules/` | Voll-Stack: UI + API + Migrationen + optionaler Dienst |

Module können die beiden unteren Stufen nutzen (ein Modul mit `has_service: true` betreibt
intern ein Extension-Script). Das Modulsystem ist ein **Parallel-System zum Plugin-System**
mit eigenem Loader, Registry, Installer und Hub-Client — gleiches Muster, eigene Tabellen.

### Manifest (`manifest.json`)
- Pflichtfelder `id` (kebab/lowercase, `[a-z0-9][a-z0-9-]*`), `name`, `version`.
- Optionale Felder: `icon` (lucide-Icon-Name, Default `"Boxes"`), `nav_group` (Default `"working"`),
  `permissions` (Liste), `has_service` (Bool, Default `false`), `min_core_version`.
- `id` ist der eindeutige Schlüssel und bildet zugleich Verzeichnis- und URL-Prefix.
  (`manifest.py:6,13-40`)

### ModuleContext — der Vertrag (`context.py`)
Das Backend eines Moduls implementiert `register(ctx: ModuleContext) -> None`.
`ModuleContext` akkumuliert, was das Modul registriert:

| Methode | Effekt |
|---------|--------|
| `ctx.register_router(router)` | FastAPI `APIRouter`, wird unter `/api/modules/<id>/…` eingehängt |
| `ctx.register_migrations(rel_dir)` | relativer Pfad zum SQL-Ordner des Moduls |
| `ctx.register_service(rel_dir)` | optionaler Extension-Ordner (`install.sh`/`uninstall.sh`) |

(`context.py:6-22`)

### Registry (`registry.py`)
- `LoadedModule`-Dataclass: `name`, `manifest`, `path`, `ctx`, `loaded` (bool), `error` (str|None).
- `REGISTRY: dict[str, LoadedModule]` — Modul-Name als Schlüssel, Prozess-globales Dict,
  wird bei `load_all()` zurückgesetzt und neu befüllt. (`registry.py:8-18`)

### Loader (`loader.py`)
- **`load_all()`** — idempotent, beim Backend-Start einmal aufgerufen. Scannt
  `settings.modules_dir`, liest je ein `manifest.json`, importiert `backend/__init__.py`
  per `importlib.util.spec_from_file_location` (exaktes Plugin-Loader-Muster,
  `plugins/loader.py`), ruft `register(ctx)`, wendet Migrationen an. (`loader.py:81-97`)
- **`_import_backend(module_dir, mid)`** — legt `sys.path`-Eintrag + `sys.modules`-Registrierung
  `hhmod_<id>` an; bleibt für die Prozess-Laufzeit — Entfernen eines Moduls erfordert Restart
  (by design). (`loader.py:23-47`)
- **Fehler-Isolation**: jedes Modul in eigenem `try/except` — ein kaputtes Modul blockt die
  anderen nicht; `LoadedModule.error` enthält die Meldung, `loaded=False`. (`loader.py:50-78`)

### Migrationen — pro Modul versioniert (`migrations.py`)
- **`apply_module_migrations(module_id, migrations_dir)`** — scannt `NNN_*.sql` (sortiert),
  wendet ausstehende Versionen an, trackt in `module_schema_version`. (`migrations.py:30-60`)
- **`module_schema_version`-Tabelle** (Core-Migration 027): `PRIMARY KEY (module_id, version)` —
  getrennt von der Core-`schema_version` (kein Integer-Konflikt).
  (`db/migrations/027_module_schema_version.sql`, `migrations.py:19-27`)
- Partiell-Migrations-Schutz: `duplicate column name`/`already exists` → warnen + als erledigt
  markieren (robustheit gegen Partial-Runs). (`migrations.py:50-53`)
- **Daten-bleiben-Garantie**: Deinstall fasst `module_schema_version` und Modul-Tabellen **nicht
  an**. Re-Install: Versionen schon getrackt → kein Re-Run → alle Daten intakt.
  (`installer.py:84-97`, Kommentar `migrations.py:31-33`)

### Hub-Client (`hub_client.py`)
- **`refresh()`** — stellt sicher, dass der Hub-Cache aktuell ist: `git pull --ff-only` bei
  vorhandenem Cache, sonst `git clone --depth=1 --filter=blob:none`. Wirft `HubError` bei
  Git-Fehler. (`hub_client.py:29-47`)
- **`read_hub_index()`** — liest `hub.json` aus dem Cache, ruft `refresh()` bei Bedarf.
  (`hub_client.py:50-58`)
- **`module_source_path(module_path)`** — löst `hub.json`-Pfad zu absolutem Cache-Pfad auf,
  prüft via `relative_to()` echte Verzeichnis-Grenze (kein String-Prefix, Path-Traversal-Schutz).
  (`hub_client.py:61-69`)
- Settings: `settings.module_hub_cache` = `<data_dir>/.module-cache/hub`,
  `settings.module_hub_git_url` (Env `HH_MODULE_HUB_GIT_URL`, Default
  `https://github.com/hydrahive/hydrahive2-modules.git`). (`settings/_paths.py:54-63`)

### Installer (`installer.py`) — Install/Deinstall-Pipeline
- **`copy_module_in(module_id)`** — Hub refreshen + Source via `hub.json` finden → Backend
  nach `settings.modules_dir/<id>` kopieren (`shutil.copytree`, `symlinks=False` kein Symlink-
  Escape) → Frontend-Assets nach `<base_dir>/frontend/src/modules/<id>` kopieren.
  (`installer.py:56-81`)
- **`remove_module_files(module_id)`** — entfernt `modules_dir/<id>` und
  `frontend/src/modules/<id>`. DB/Daten bleiben. (`installer.py:84-97`)
- **`install(module_id)`** → Generator: Dateien kopieren → ggf. `extension/install.sh` (falls
  `has_service`) → `npm run build` → `.restart_request` schreiben. (`installer.py:124-131`)
- **`uninstall(module_id)`** → Generator: ggf. `extension/uninstall.sh` → Dateien entfernen
  (Daten bleiben) → `npm run build` → `.restart_request`. (`installer.py:134-141`)
- Module-ID-Validation via Regex vor jeder Datei-Operation (Path-Traversal-Guard).
  (`installer.py:33-38`)
- **Restart-Mechanik**: `data_dir/.restart_request` schreiben → bestehender systemd-Path-Watcher
  startet Backend neu → `load_all()` + Migrationen + Router. Kein Core-git-pull (anders als
  `.update_request`). (`installer.py:109-111`)

### HTTP-API (`api/routes/modules.py`, Prefix `/api/admin/modules`)
- **Admin-only** (alle Endpunkte via `Depends(require_admin)`).
- `GET /api/admin/modules` — liefert `{installed: [LoadedModule-Daten], available: [hub.json-Einträge]}`.
  Hub unerreichbar → `available: []` + Warning-Log, kein 500. (`routes/modules.py:22-38`)
- `POST /api/admin/modules/{module_id}/install` → SSE-Stream des `installer.install()`-Generators.
  (`routes/modules.py:50-52`)
- `DELETE /api/admin/modules/{module_id}` → SSE-Stream des `installer.uninstall()`-Generators.
  (`routes/modules.py:55-57`)
- SSE-Format: `data: {"line": "..."}` (Fortschritt) + abschließend `data: {"done": true}`.
  (`routes/modules.py:41-47`)

### Lifespan-Verdrahtung (`api/lifespan.py`, `api/main.py`)
- Reihenfolge beim Start: `plugin_system.load_all()` → `module_system.load_all()` →
  `mount_module_routers(app)`. (`lifespan.py:119-123`)
- **`mount_module_routers(target_app)`** — iteriert `REGISTRY`, hängt jeden Router mit
  `prefix=/api/modules/<id>` ein; Fehler pro Router isoliert (kein Start-Abbruch).
  (`main.py:163-175`)

### Settings (`settings/_paths.py`)
- `settings.modules_dir` = `data_dir / "modules"` (cached_property, lazy). (`_paths.py:50-52`)
- `settings.module_hub_cache` = `data_dir / ".module-cache" / "hub"`. (`_paths.py:54-56`)
- `settings.module_hub_git_url` = `HH_MODULE_HUB_GIT_URL` oder `https://github.com/hydrahive/hydrahive2-modules.git`. (`_paths.py:58-63`)
- `settings.base_dir` (bestehend) zeigt auf `/opt/hydrahive2` — Installer leitet daraus
  `frontend/src/modules/` ab. (`installer.py:42-43`)

---

## Frontend

### Codegen (`frontend/scripts/gen-modules.mjs`)
- Wird als **`prebuild`**-Script bei jedem `npm run build` ausgeführt
  (also bei Install und Deinstall). (`package.json:9`)
- Scannt `frontend/src/modules/` nach Unterverzeichnissen mit `index.tsx`, importiert alle,
  aggregiert `routes`, `nav`, `i18n` zu `src/modules/index.generated.ts`. (`gen-modules.mjs:8-24`)
- `index.generated.ts` und `src/modules/*/` sind **gitignored** — kein Modul-Code im Core-Repo.
- Bei keinen installierten Modulen: leere Arrays → Build hat kein Problem.

### Drei Core-Hooks (einmalig, nie pro Modul ändern)

| Datei | Hook |
|-------|------|
| `frontend/src/App.tsx:6,106-108` | `moduleRoutes` → `{appModuleRoutes.map(r => <Route .../>)}` in geschützten Routen |
| `frontend/src/shared/nav-config.ts:6,75-84` | `moduleNav` → `MODULE_NAV_ITEMS` (Icon-Name via `moduleIcon()` aufgelöst) + in `visibleItems()` |
| `frontend/src/i18n/index.ts:4,112-114` | `moduleI18n` → in `mergedResources` gemergt vor `i18n.init()` |

- **`shared/module-icon.ts`** — `moduleIcon(name: string): LucideIcon` — löst lucide-Icon-Name
  (String aus dem Frontend-Manifest) zu Komponente auf, Fallback `Icons.Boxes`. (`module-icon.ts:8-11`)

### Admin-UI (`frontend/src/features/modules/`)
- `types.ts` — `InstalledModule`, `AvailableModule`, `ModulesIndex`. (`types.ts:1-17`)
- `api.ts` — `listModules()` (GET), `installModule()` + `uninstallModule()` (POST/DELETE als
  SSE-Stream, `fetch` + `ReadableStream`-Reader, `AbortController`). (`api.ts:12-74`)
- `ModulesPage.tsx` — zwei Sektionen „installiert" / „verfügbar" mit Grid-Layout, Refresh-Button.
  Admin-only (Route in `App.tsx:102` via `AdminGuard`). (`ModulesPage.tsx:8-90`)
- `ModuleCard.tsx` — `InstalledModuleCard` (Status loaded/error + Deinstall-Button +
  SSE-Log-Fenster) / `AvailableModuleCard` (Install-Button + SSE-Log-Fenster). Log-Zeilen
  farbcodiert: `[OK]` grün, `[FEHLER]`/`[ERROR]` rot, `[WARN]` gelb. (`ModuleCard.tsx:16-187`)
- Routing: `App.tsx:102` `/modules` → `<AdminGuard><ModulesPage /></AdminGuard>`.
- Nav: `nav-config.ts:67` fester Core-Eintrag `/modules`, Icon `Boxes`, Gruppe `settings`, Admin-only.
- i18n: Namespace `modules` de+en (`i18n/locales/{de,en}/modules.json`).

---

## Template-Modul `example` (Walking Skeleton + offizielle Vorlage)

Liegt unter `modules/example/` im Repo — Referenz für neue Module, über den Hub installierbar.

### Anatomie
- `manifest.json` — id `example`, name `Beispiel-Modul`, v1.0.0, `has_service: false`.
  (`modules/example/manifest.json`)
- `backend/__init__.py` — `register(ctx)` registriert Router (`GET/POST /notes`) + Migrationen.
  Kein Auth-Bypass: Routen via `Depends(require_auth)`. (`modules/example/backend/__init__.py:40-42`)
- `migrations/001_example.sql` — `CREATE TABLE IF NOT EXISTS module_example_notes(id, text, created_at)`.
  (`modules/example/migrations/001_example.sql`)
- `frontend/index.tsx` — exportiert `routes` (1 Route `/example`), `nav` (1 Nav-Eintrag),
  `i18n` (de+en). Das sind die drei Werte, die `gen-modules.mjs` aggregiert.
  (`modules/example/frontend/index.tsx:3-34`)
- `frontend/ExamplePage.tsx` — Liste + Eingabe, liest/schreibt via `/api/modules/example/notes`.
  Vollständiger UI↔API↔DB-Beweis. (`modules/example/frontend/ExamplePage.tsx:11-94`)

---

## WIE  (Datenflüsse)

### Install-Pipeline (Klick → Modul live)
```
Admin klickt „Installieren"
  → POST /api/admin/modules/{id}/install
  → installer.install(id) Generator (SSE-Stream an Frontend):
      1. hub_client.refresh()            → git clone/pull hub-Repo
      2. copy_module_in(id)              → copytree Backend → modules_dir/<id>
                                         → copytree Frontend → src/modules/<id>
      3. (has_service?) install.sh       → Dienst hochfahren
      4. npm run build                   → prebuild: gen-modules.mjs schreibt index.generated.ts
                                         → tsc -b && vite build (dist mit Modul-UI)
      5. .restart_request schreiben      → systemd-Path-Watcher → Restart
         Backend-Start: load_all()       → _import_backend + register(ctx)
                      apply_module_migrations() → NNN_*.sql neu anwenden
                      mount_module_routers()    → include_router /api/modules/<id>/...
  → SSE: "data: {\"done\": true}"
```

### Deinstall-Pipeline (Daten bleiben)
```
Admin klickt „Deinstallieren"
  → DELETE /api/admin/modules/{id}
  → installer.uninstall(id) Generator:
      1. (has_service?) uninstall.sh     → Dienst stoppen/entfernen
      2. remove_module_files(id)         → rmtree modules_dir/<id>
                                         → rmtree src/modules/<id>
         (DB-Tabellen + module_schema_version BLEIBEN)
      3. npm run build                   → gen-modules.mjs: Modul weg aus Index
                                         → dist ohne Modul-UI
      4. .restart_request                → Restart
         Backend-Start: load_all()       → Modul weg aus REGISTRY
                      mount_module_routers() → kein Router für dieses Modul
  → Re-Install: Migrationen schon getrackt → kein Re-Run → Daten intakt
```

### Re-Install / Daten-bleiben-Mechanik
`module_schema_version` enthält `(module_id, version, applied_at)`. Bei Re-Install
vergleicht `apply_module_migrations` den Max-Wert aus der Tabelle mit den SQL-Dateien —
bereits angewendete Versionen werden übersprungen. DB-Tabellen des Moduls existieren noch
(Deinstall hat sie nicht angefasst) → `CREATE TABLE IF NOT EXISTS` läuft trotzdem durch.
Netto: Daten aus der Vorgänger-Installation stehen sofort zur Verfügung.

### Backend-Start (normaler Betrieb, kein Install)
```
lifespan.startup():
  ...
  plugin_system.load_all()
  module_system.load_all()     ← REGISTRY aufbauen + Migrationen
  mount_module_routers(app)    ← Router eingehängen
  ...
```

---

## WO  (Datei:Zeile)

| Datei | Inhalt |
|-------|--------|
| `core/src/hydrahive/modules/manifest.py:6,13` | `ModuleManifest`, ID-Regex, `load()` |
| `core/src/hydrahive/modules/context.py:6` | `ModuleContext` — Vertrag `register(ctx)` |
| `core/src/hydrahive/modules/registry.py:8,18` | `LoadedModule`, `REGISTRY` dict |
| `core/src/hydrahive/modules/loader.py:23,50,81` | `_import_backend`, `_load_one`, `load_all` |
| `core/src/hydrahive/modules/migrations.py:19,30` | `_ensure_module_version_table`, `apply_module_migrations` |
| `core/src/hydrahive/modules/hub_client.py:16,29,50,61` | `HubError`, `refresh`, `read_hub_index`, `module_source_path` |
| `core/src/hydrahive/modules/installer.py:29,56,84,104,124,134` | `InstallError`, `copy_module_in`, `remove_module_files`, Orchestrierung, `install`, `uninstall` |
| `core/src/hydrahive/api/routes/modules.py:17,22,50,55` | Router-Definition, `list_modules`, `install_module`, `uninstall_module` |
| `core/src/hydrahive/api/main.py:163` | `mount_module_routers` |
| `core/src/hydrahive/api/lifespan.py:119-123` | `module_system.load_all()` + `mount_module_routers()` im Startup |
| `core/src/hydrahive/settings/_paths.py:50-63` | `modules_dir`, `module_hub_cache`, `module_hub_git_url` |
| `core/src/hydrahive/db/migrations/027_module_schema_version.sql` | Core-Migration für Modul-Versions-Tracking |
| `modules/example/manifest.json` | Template-Manifest |
| `modules/example/backend/__init__.py` | Template-Backend, `register(ctx)` |
| `modules/example/migrations/001_example.sql` | Template-Migration |
| `modules/example/frontend/index.tsx` | Template-Frontend-Deklaration (routes/nav/i18n) |
| `modules/example/frontend/ExamplePage.tsx` | Template-UI |
| `frontend/scripts/gen-modules.mjs` | Codegen-Script (prebuild) |
| `frontend/src/modules/index.generated.ts` | aggregierte Module (gitignored, prebuild) |
| `frontend/src/features/modules/types.ts` | `InstalledModule`, `AvailableModule` |
| `frontend/src/features/modules/api.ts` | `listModules`, `installModule`, `uninstallModule` (SSE) |
| `frontend/src/features/modules/ModulesPage.tsx` | Admin-UI Hauptseite |
| `frontend/src/features/modules/ModuleCard.tsx` | Install/Uninstall-Karten mit SSE-Log |
| `frontend/src/App.tsx:6,9,106-108` | `moduleRoutes` eingehängt |
| `frontend/src/shared/nav-config.ts:6,75-84` | `MODULE_NAV_ITEMS` aus `moduleNav` |
| `frontend/src/shared/module-icon.ts:8` | `moduleIcon(name)` → LucideIcon-Resolver |
| `frontend/src/i18n/index.ts:4,112-114` | `moduleI18n` in `mergedResources` gemergt |
| `frontend/package.json:9` | `"prebuild": "... node scripts/gen-modules.mjs"` |

---

## WARUM  (nicht-offensichtliche Verdrahtung, Gotchas)

- **Rebuild statt Runtime-Loading**: Module-Federation / lazy-load bei Install war bewusst
  verworfen (Komplexität, kein echter Vorteil für ein self-hosted System). `npm run build` inline
  im Install-Generator — der Admin sieht das Log, wartet, done.
- **Restart statt Router-Injizieren**: FastAPI-Router können zwar zur Laufzeit eingehängt werden,
  aber Compaction/Session-State und importlib-Module-Cache machen einen sauberen Restart
  einfacher und sicherer. Der systemd-Path-Watcher ist bereits für Updates verdrahtet.
- **DB-Tabellen bleiben immer**: keine Down-Migrationen, kein automatisches Löschen. Das ist
  Absicht (YAGNI + Datensicherheit). Expliziter Purge wäre v2.
- **Keine Symlinks (`symlinks=False`)**: beim `copytree` explizit deaktiviert — ein bösartiger
  Hub könnte sonst via Symlink-Escape aus dem Hub-Cache herauszeigen. (`installer.py:70`)
- **Path-Traversal-Guard an zwei Stellen**: `_ID_RE`-Validation vor allen Datei-Ops
  (`installer.py:33-38`) + `module_source_path` via `relative_to()` statt String-Prefix
  (`hub_client.py:65-68`). Modul-IDs sind kebab/lowercase, kein `../`.
- **`sys.path`-Eintrag bleibt im Prozess**: nach Deinstall + Restart ist der alte `hhmod_<id>`-
  Eintrag weg (REGISTRY leer, `load_all()` hat ihn nicht neu angelegt). Aber `sys.path` aus
  einem vorherigen Load bleibt im alten Prozess — daher Restart. Der neue Prozess startet sauber.
- **Hub unerreichbar → kein 500**: `list_modules` fängt `HubError` und liefert `available: []`
  mit Warning-Log. Install schlägt dann mit `HubError` fehl (wird im SSE-Log sichtbar).
- **`gen-modules.mjs` erstellt `src/modules/` falls nicht vorhanden** (`mkdirSync(modulesDir, {recursive: true})`)
  — robustheit auf frischem Checkout ohne installierte Module. (`gen-modules.mjs:7`)
- **Icon als String, nicht Import**: das Modul-Manifest/Frontend deklariert Icons als lucide-Namen
  (`"Boxes"`); der Core resolvet via `moduleIcon()` — dadurch kein Import aus dem Modul-Code in
  Core-Dateien, keine Build-Zeit-Abhängigkeit.
- **Muster-Konsistenz mit Plugin-System**: `_import_backend` folgt exakt `plugins/loader.py`,
  `hub_client.py` folgt `plugins/hub_client.py`, `installer.py` folgt `plugins/installer.py`.
  Wer Plugins kennt, kennt Module.

---

## Datenmodell / Settings

- **`module_schema_version`** (Core-Tabelle, Migration 027): `module_id TEXT, version INTEGER, applied_at TEXT`, PK `(module_id, version)`.
- **Env-Keys**: `HH_MODULE_HUB_GIT_URL` (Default: GitHub-Repo hydrahive/hydrahive2-modules).
- **Pfade**:
  - Backend: `<data_dir>/modules/<id>/` (manifest + backend/ + migrations/ + ggf. extension/)
  - Frontend: `<base_dir>/frontend/src/modules/<id>/` (gitignored, nur bei Install vorhanden)
  - Hub-Cache: `<data_dir>/.module-cache/hub/`
  - Restart-Trigger: `<data_dir>/.restart_request`
- **URL-Namespace**: Backend `/api/admin/modules` (Admin-API) + `/api/modules/<id>/…` (Modul-APIs).
- **Frontend-Route** `/modules` (Admin-only), Nav-Label `modules` (i18n-Key), Gruppe `settings`.
- **i18n**: Namespace `modules` (Core-Strings der Admin-UI); Modul-eigene Namespaces kommen via `moduleI18n`.

---

## Tests

- `core/tests/test_module_manifest.py` — `ModuleManifest.load` + ID-Validierung
- `core/tests/test_module_context.py` — `ModuleContext`-Akkumulation
- `core/tests/test_module_loader.py` — `load_all`: Fake-Modul-Dirs, Fehler-Isolation, idempotent
- `core/tests/test_module_migrations.py` — apply + idempotent + Daten-bleiben-Semantik
- `core/tests/test_module_hub.py` — `hub_client` (git gemockt, Path-Traversal-Ablehnung)
- `core/tests/test_module_installer.py` — `copy_module_in`/`remove_module_files`, Traversal-Guard
- `core/tests/test_module_install_flow.py` — `install`/`uninstall` Generator (FS/Build/Restart gemockt)
- `core/tests/test_modules_routes.py` — `/api/admin/modules` Endpunkte
- `core/tests/test_modules_main_wiring.py` — `mount_module_routers` Fehler-Isolation
- `core/tests/test_modules_settings.py` — `modules_dir`, `module_hub_*` Settings
- `core/tests/test_example_module.py` — Template-Modul `register(ctx)`-Vertrag
- **Frontend**: `npm run build` grün nach Codegen (Template-Modul im Build-Durchlauf nachgewiesen).
- **Live-E2E (Till, 2026-06-04)**: Template über Button installieren → Nav + Seite erscheinen,
  Notes schreiben → deinstallieren → alles weg → re-install → Notes wieder da.

---

## Offene Enden / YAGNI

- **Module-Federation / Runtime-Loading** — bewusst nicht in v1 (Rebuild reicht).
- **Down-Migrationen / Daten-Purge** — explizite „Daten endgültig löschen"-Aktion = v2.
- **Versions-/Abhängigkeits-Auflösung** zwischen Modulen — v1: jedes Modul ist eigenständig.
- **Community-/Dritt-Module + Sandboxing** — v1: first-party Hub, vertrauenswürdiger Code.
- **Erstes echtes Modul** (Notizbuch, Team-Chat-Migration etc.) — eigene Sub-Projekte mit eigenem Spec.
