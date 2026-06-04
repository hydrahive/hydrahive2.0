# Feature Map: Modulsystem v1

Dritte Extensibility-Stufe: **Voll-Stack-Module** — UI + API + Migrationen + optionaler Dienst
als install/deinstallierbare Einheit. Install/Uninstall = Dateien kopieren/entfernen + Frontend-
Rebuild + Backend-Restart. **Modul-Daten bleiben bei Deinstall erhalten.**
Der Core wird einmalig mit drei statischen Hooks verdrahtet, dann nie wieder pro Modul angefasst.

Volle Referenz mit `datei:zeile`: [`../28-modules.md`](../28-modules.md).

## Drei Extensibility-Stufen

| Stufe | Verzeichnis | Enthält |
|-------|-------------|---------|
| Plugin | `plugins/` | Agent-Tools (bestehend) |
| Extension | `extensions/` | Dienste (install/uninstall-Scripts, z.B. tuwunel) |
| **Modul** | `<data_dir>/modules/` | Voll-Stack: UI + API + Migrations + opt. Dienst |

Module können Plugins und Extensions als Bausteine nutzen. Das Modulsystem ist ein
**Parallel-System** zum Plugin-System (eigener Loader/Registry/Installer/Hub, gleiches Muster).

## Dateien

| Datei | Rolle |
|-------|-------|
| `modules/manifest.py` | `ModuleManifest` — Pflichtfelder id/name/version, Regex-Validierung, frozen dataclass |
| `modules/context.py` | `ModuleContext` — Vertrag `register(ctx)`: router + migrations + service |
| `modules/registry.py` | `LoadedModule` dataclass + `REGISTRY: dict[str, LoadedModule]` |
| `modules/loader.py` | `load_all()` — scannt modules_dir, importlib-Import, Fehler-Isolation pro Modul |
| `modules/migrations.py` | `apply_module_migrations` — NNN_*.sql trackt in `module_schema_version` |
| `modules/hub_client.py` | git-Cache des Hub-Repos (`hub.json`), `refresh`, Path-Traversal-Schutz |
| `modules/installer.py` | `copy_module_in`/`remove_module_files` + `install`/`uninstall`-Generatoren |
| `api/routes/modules.py` | `/api/admin/modules` list/install/uninstall (Admin-only, SSE-Stream) |
| `api/main.py` | `mount_module_routers()` — Router aller geladenen Module eingehängt |
| `api/lifespan.py` | `module_system.load_all()` + `mount_module_routers()` beim Start |
| `settings/_paths.py` | `modules_dir`, `module_hub_cache`, `module_hub_git_url` |
| `db/migrations/027_module_schema_version.sql` | Core-Tabelle für Modul-Versions-Tracking (getrennt von `schema_version`) |
| `modules/example/` | Template-Modul (Walking Skeleton): manifest + backend + migration + frontend |
| `frontend/scripts/gen-modules.mjs` | prebuild-Codegen: scannt `src/modules/*/index.tsx`, schreibt `index.generated.ts` |
| `frontend/src/modules/index.generated.ts` | aggregierte routes/nav/i18n aller installierten Module (gitignored) |
| `frontend/src/features/modules/` | Admin-UI: `types.ts` / `api.ts` / `ModulesPage.tsx` / `ModuleCard.tsx` |
| `frontend/src/App.tsx` | Core-Hook: `moduleRoutes` → `<Route>` (einmalig) |
| `frontend/src/shared/nav-config.ts` | Core-Hook: `moduleNav` → `MODULE_NAV_ITEMS` (einmalig) |
| `frontend/src/i18n/index.ts` | Core-Hook: `moduleI18n` → `mergedResources` (einmalig) |
| `frontend/src/shared/module-icon.ts` | `moduleIcon(name)` — lucide-Icon-Name → LucideIcon-Komponente |

## Datenfluss Install → Build → Restart → Load → Mount

```
Admin POST /api/admin/modules/{id}/install
  → installer.install() Generator → SSE-Stream an UI:
     1. hub_client.refresh()        → git clone/pull github.com/hydrahive/hydrahive2-modules
     2. copy_module_in(id)          → copytree backend → <data_dir>/modules/<id>/
                                      copytree frontend → frontend/src/modules/<id>/
     3. [has_service] install.sh    → Extension-Dienst hochfahren
     4. npm run build               → gen-modules.mjs schreibt index.generated.ts
                                      → tsc -b && vite build
     5. .restart_request            → systemd-Path-Watcher → Restart
        lifespan.startup():
           module_system.load_all() → importlib backend/__init__.py → register(ctx)
                                      apply_module_migrations() → NNN_*.sql
           mount_module_routers()   → app.include_router /api/modules/<id>/...
  → "data: {\"done\": true}"
```

**Deinstall** (DELETE): Dienst stoppen → Dateien entfernen (**DB/Daten unangetastet**) → Rebuild → Restart.

## Daten-bleiben-Mechanik

`module_schema_version (module_id, version, applied_at)` bleibt bei Deinstall. Re-Install:
schon getrackte Versionen werden übersprungen → `CREATE TABLE IF NOT EXISTS` läuft durch →
vorhandene Daten intakt. Expliziter Purge = v2 (YAGNI).

## Modul-Vertrag (`register(ctx)`)

```python
def register(ctx: ModuleContext) -> None:
    ctx.register_router(router)          # FastAPI APIRouter → /api/modules/<id>/...
    ctx.register_migrations("migrations") # NNN_*.sql im Modul-Dir
    # ctx.register_service("extension")  # optional: install/uninstall.sh
```

## Frontend-Codegen-Flow

1. `npm run build` ruft `prebuild` auf → `node scripts/gen-modules.mjs`
2. Script scannt `src/modules/*/index.tsx` → schreibt `index.generated.ts`
3. Generierte Datei exportiert `moduleRoutes`, `moduleNav`, `moduleI18n`
4. Drei Core-Hooks (einmalig eingebaut, nie pro Modul geändert):
   - `App.tsx` — `moduleRoutes` als `<Route>`-Elemente
   - `nav-config.ts` — `moduleNav` in `visibleItems()` (Icon via `moduleIcon()`)
   - `i18n/index.ts` — `moduleI18n`-Bundles in `mergedResources` gemergt

## Hub

Erstes Party-Hub: `github.com/hydrahive/hydrahive2-modules` (Env `HH_MODULE_HUB_GIT_URL`).
Hub-Cache: `<data_dir>/.module-cache/hub/`. `hub.json` im Cache-Repo enthält Index der
verfügbaren Module. Path-Traversal-Schutz: `hub_client.module_source_path` via `relative_to()`.

## Verwandte Subsysteme

- **Plugins** ([`12-plugins.md`](../12-plugins.md)) — Loader/Hub-Muster übernommen; Tools-Ebene.
- **Extensions** ([`12-plugins.md`](../12-plugins.md)) — Service-Ebene; Module können `has_service: true` setzen.
- **DB & Persistence** ([`18-db.md`](../18-db.md)) — `module_schema_version` als neue Core-Tabelle (Migration 027).
- **System & Admin** ([`22-system.md`](../22-system.md)) — `.restart_request` Mechanik (systemd-Path-Watcher).

## Status

v1 komplett auf `main` (2026-06-04). Template-Modul `example` ist Walking Skeleton und offizielle
Vorlage. Nächste Sub-Projekte: erstes echtes Modul (Notizbuch), Team-Chat als Modul migrieren
(echter Service-Proof), User-/Gruppen-Management.
