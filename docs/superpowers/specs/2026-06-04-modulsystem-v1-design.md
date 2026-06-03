# Modulsystem v1 — Design (Sub-Projekt 1: Framework + Template-Modul)

> **Ziel:** Voll-Stack-Features als austauschbare **Module** — je eigenes Git-Repo, im
> HydraHive per Knopf installier-/deinstallierbar. Install bringt alle Menüs/Seiten/API/
> Dienste; Deinstall entfernt alles **außer den angefallenen Modul-Daten** (Re-Install
> findet sie wieder). Architektur-Antwort auf das HH1-Monolith-Trauma: der Core bleibt
> schlank, Features kommen/gehen ohne Kollateralschaden.
>
> **Scope dieses Specs = Sub-Projekt 1:** das Modul-Framework (Vertrag, Loader,
> Install/Deinstall-Pipeline, Frontend-Rebuild) **bewiesen mit einem Minimal-Template-Modul**
> (Walking Skeleton). Echte Module (Notizbuch, Team-Chat-Migration, …) sind eigene
> Sub-Projekte mit eigenem Spec.
>
> **Status:** Design abgestimmt (Brainstorming 2026-06-04). Roadmap: `docs/ROADMAP.md`.

---

## Entscheidungen (abgestimmt)

| Frage | Entscheidung |
|---|---|
| Frontend rein/raus | **Rebuild beim Install** (`npm run build`), nicht Module-Federation, nicht „nur ausblenden" |
| Backend rein/raus | **Restart beim Install** (Loader liest beim Start) — kein Router-Injizieren zur Laufzeit |
| Deinstall + Daten | UI/Code/Routen/Dienst weg, **DB-Tabellen + Daten bleiben** (Re-Install-fähig) |
| Verhältnis Plugins/Extensions | Modul ist die Voll-Stack-Klammer **über** ihnen; Plugins (Tools) + Extensions (Dienste) bleiben als Bausteine. Modulsystem = **Parallel-System zum Plugin-System** (eigener Installer/Loader/Registry/Hub, gleiches Muster) |
| Quelle/Trust v1 | **first-party Modul-Hub** (git-Repo + `hub.json`, wie Plugin-Hub); Module = vertrauenswürdiger Code mit vollen Rechten; kein Dritt-Sandbox |
| Erstes Modul | Minimal-**Template-Modul** `example` (bleibt als offizielle Vorlage) |

---

## Architektur

Drei Stufen, von schmal nach breit:
- **Plugin** (`plugins/`): nur Agent-Tools. Bleibt.
- **Extension** (`extensions/`): nur Dienste (Install/Uninstall-Scripts, z.B. tuwunel). Bleibt.
- **Modul** (NEU, `modules/`): Voll-Stack — UI + API + Migrationen + optional Dienst, als eine
  install/deinstallierbare Einheit, je eigenes Repo. Kann die beiden unteren Bausteine nutzen.

Der Core wird für Module **genau einmal** angefasst (drei statische Hooks, dann nie wieder pro Modul):
`api/main.py` (Modul-Router einhängen), `frontend/src/App.tsx` (Modul-Routen), `frontend/src/shared/nav-config.ts`
(Modul-Nav) — alle drei lesen aus generierten Registries, nicht aus pro-Modul-Code.

---

## Modul-Anatomie (ein Git-Repo)

```
<modul-repo>/
  manifest.json
  backend/
    __init__.py          # def register(ctx: ModuleContext) -> None
    ...                  # Router, Logik
  migrations/
    001_*.sql            # pro Modul versioniert
  frontend/
    index.tsx            # export { routes, nav, i18n }
    ...                  # Seiten/Komponenten
  extension/             # optional: install.sh / uninstall.sh (Extension-System) für einen Dienst
```

### `manifest.json`
```json
{
  "id": "example",
  "name": "Beispiel-Modul",
  "version": "1.0.0",
  "icon": "Boxes",
  "nav_group": "working",
  "permissions": ["example.use"],
  "has_service": false,
  "min_core_version": "2.0.0"
}
```
`id` ist der eindeutige Schlüssel (kebab/lowercase, Matrix-/Pfad-sicher). `icon`/`nav_group` sind
Metadaten für die Admin-Liste; das tatsächliche Nav kommt aus `frontend/index.tsx`.

### `backend/__init__.py` — der Vertrag
```python
def register(ctx: ModuleContext) -> None:
    ctx.register_router(router)            # FastAPI APIRouter, prefix /api/modules/<id>
    ctx.register_migrations("migrations")  # relativ zum Modul-Dir
    # ctx.register_service("extension")    # optional
```

### `frontend/index.tsx` — UI-Deklaration (einzige Quelle für Nav+Routen)
```tsx
export const routes = [{ path: "/example", element: <ExamplePage /> }]
export const nav    = [{ path: "/example", icon: "Boxes", labelKey: "example", group: "working", roles: [] }]
export const i18n   = { de: { example: { /* … */ } }, en: { example: { /* … */ } } }
```

---

## Backend

### `core/src/hydrahive/modules/`
- **`context.py` — `ModuleContext`**: akkumuliert, was ein Modul registriert.
  - `register_router(router: APIRouter)` — wird nach dem Laden via `app.include_router` eingehängt.
  - `register_migrations(rel_dir: str)` — Pfad zum Migrations-Ordner des Moduls.
  - `register_service(rel_dir: str)` — optionaler Extension-Ordner (install/uninstall-Scripts).
- **`loader.py` — `load_all()`**: beim Backend-Start. Scannt `<data_dir>/modules/*`, liest `manifest.json`,
  importiert `backend/__init__.py` per importlib (**exakt das Plugin-Loader-Muster**,
  `plugins/loader.py:43-66`), ruft `register(ctx)`. Baut die `ModuleRegistry`. **Fehler isoliert pro
  Modul** (ein kaputtes Modul blockiert die anderen nicht; geloggt).
- **`registry.py` — `ModuleRegistry`**: Liste geladener Module (id, manifest, router, migrations_dir,
  service_dir, loaded/error).
- **`installer.py`**: install/uninstall/update gegen den Hub-Cache (Muster `plugins/installer.py`:
  `copytree`/`rmtree`). Plus die Modul-spezifischen Schritte (Frontend-Codegen, Build, Service-Hook).
- **`hub_client.py`**: git-Cache des Modul-Hubs (`hub.json`-Index), Muster `plugins/hub_client.py`.

### Router-Registrierung (`api/main.py`)
Nach `modules.load_all()`: für jeden Registry-Eintrag `app.include_router(entry.router)`. Modul-APIs leben
unter `/api/modules/<id>/…`. Neue Router erscheinen beim (Neu-)Start → daher Restart bei Install.

### Migrationen — pro Modul versioniert (Daten-bleiben-Kern)
- Neue Tabelle (Core-Migration im Modulsystem-Setup):
  ```sql
  CREATE TABLE IF NOT EXISTS module_schema_version (
      module_id   TEXT NOT NULL,
      version     INTEGER NOT NULL,
      applied_at  TEXT NOT NULL,
      PRIMARY KEY (module_id, version)
  );
  ```
- `apply_module_migrations(module_id, migrations_dir)`: scannt `NNN_*.sql` (sortiert), wendet ausstehende an,
  trackt in `module_schema_version`. Läuft beim Load (Start) für jedes installierte Modul. **Getrennt vom
  Core-`schema_version`** → kein Integer-Kollidieren.
- **Deinstall fasst Tabellen/Daten + `module_schema_version` NICHT an.** Re-Install: Versionen schon getrackt
  → kein Re-Run → Daten intakt. (Eine separate „Daten endgültig löschen"-Aktion ist v2, nicht Teil von Deinstall.)

---

## Frontend

- Modul deklariert UI in `frontend/index.tsx` (`routes`, `nav`, `i18n`).
- **Codegen `frontend/src/modules/index.generated.ts`** (bei jedem Install/Deinstall neu): importiert jedes
  installierte Modul und aggregiert:
  ```ts
  import * as example from "./example"
  export const moduleRoutes = [...example.routes]
  export const moduleNav    = [...example.nav]
  export const moduleI18n   = [example.i18n]
  ```
- **Einmaliger Core-Hook** (dann nie wieder pro Modul):
  - `App.tsx`: `{moduleRoutes.map(r => <Route .../>)}` in die geschützten Routen.
  - `shared/nav-config.ts`: `moduleNav` in `NAV_ITEMS` mergen (Icons via lucide-Name auflösen).
  - `i18n/index.ts`: `moduleI18n`-Bundles registrieren.
- `frontend/src/modules/<id>/` und `index.generated.ts` sind **gitignored** — Modul-Code wird installiert, nie
  in den Core-Repo committet. (Icon im Nav: Modul gibt lucide-Icon-Namen als String; ein kleiner Resolver
  mappt String→Komponente, damit das Manifest/Nav keine Imports braucht.)

---

## Install / Deinstall-Pipeline

Admin-only Endpoints mit **gestreamtem Log** (Muster `features/extensions` + `InstallModal` + `streamAction`).

**`POST /api/modules/{id}/install`:**
1. Hub: Modul-Repo in den Hub-Cache (`git clone/pull`).
2. Backend → `<data_dir>/modules/<id>/` kopieren (backend + migrations + manifest).
3. Frontend → `frontend/src/modules/<id>/` kopieren; `index.generated.ts` neu erzeugen.
4. Falls `has_service`: `extension/install.sh` (Extension-System) → Dienst hoch.
5. `npm run build` (inline, Log gestreamt) → neues dist mit Modul-UI.
6. `.restart_request` schreiben → bestehender systemd-Path-Watcher startet Backend neu → `load_all()` +
   `apply_module_migrations` + Router eingehängt.

**`DELETE /api/modules/{id}`:**
1. Falls `has_service`: `extension/uninstall.sh` (Dienst stoppen/entfernen).
2. `<data_dir>/modules/<id>/` + `frontend/src/modules/<id>/` löschen; `index.generated.ts` neu.
   **DB-Tabellen/Daten + `module_schema_version` bleiben.**
3. `npm run build` → dist ohne Modul-UI.
4. `.restart_request` → Restart → Modul weg aus Registry/Routern. Daten bleiben → Re-Install stellt alles her.

**`GET /api/modules`** (admin): installierte + im Hub verfügbare Module (für die Admin-UI).

**Restart-Mechanik:** reuse `.restart_request` (existierender systemd-Path-Watcher, `system_admin.py:29`).
Kein Core-git-pull (anders als `.update_request`). Der Endpoint baut inline, schreibt dann den Trigger.

---

## Template-Modul `example` (Walking Skeleton + offizielle Vorlage)
- `manifest.json` (id `example`, `has_service: false`).
- `backend/__init__.py`: `register(ctx)` → Router `GET/POST /api/modules/example/notes` (liest/schreibt
  `module_example_notes`) + `register_migrations`.
- `migrations/001_example.sql`: `CREATE TABLE module_example_notes(id, text, created_at)`.
- `frontend/index.tsx`: 1 Route (`ExamplePage`), 1 Nav-Eintrag „Beispiel", i18n de/en.
- `ExamplePage.tsx`: Liste + Eingabe → liest/schreibt Notes → **end-to-end UI↔API↔DB-Beweis**.
- Liegt im Repo unter `modules/example/` als Referenz + wird über den Hub installierbar gemacht.
- *(Service-Hook ist im Vertrag + nutzt das bewährte Extension-System → echter Dienst-Proof bei der
  Team-Chat-Migration, Sub-Projekt 3. Das Skelett fokussiert die neuen Teile.)*

---

## Tests
- **Backend (pytest, TDD):** `ModuleContext`-Akkumulation · `loader` (lädt Fake-Modul-Dir → `register`,
  Fehler-Isolation) · `apply_module_migrations` (apply + idempotent + **Daten bleiben bei Deinstall**) ·
  Codegen (`index.generated.ts` korrekt aus N Modul-Dirs) · `installer` install/uninstall (FS/Build/Restart
  gemockt).
- **Frontend:** `npm run build` grün nach Codegen (das Template-Modul ist im Build).
- **Live-E2E auf `.23`** (Till): Template über den Button installieren → „Beispiel" erscheint im Nav + Seite
  liest/schreibt → deinstallieren → weg → **re-install → Daten wieder da**. Finaler Beweis.

---

## Bewusst NICHT in v1 (YAGNI)
- Module-Federation / Runtime-Loading (Rebuild reicht).
- Router-Injizieren zur Laufzeit (Restart reicht).
- Dritt-/Community-Module + Sandboxing (first-party, vertrauenswürdig).
- Down-Migrationen / automatisches Daten-Löschen bei Deinstall (Daten bleiben; expliziter Purge = v2).
- Versions-/Abhängigkeits-Auflösung zwischen Modulen (ein Modul = eigenständig).

---

## Zerlegung (Kontext — eigene Specs je Sub-Projekt)
1. **Dieses Spec:** Framework + Template-Modul.
2. Erstes echtes Modul (Notizbuch).
3. Team-Chat → Modul migrieren (inkl. tuwunel-Dienst — echter Service-Proof).
4. User-/Gruppen-Management (Module deklarieren Rollen/Rechte).
5+. weitere App-Module (Kalender, Kontakte, …).

## In der Planungs-Phase zu klären (Detail, kein Design-Blocker)
- Codegen als Python-Funktion im `installer` (testbar) vs. node-Script.
- Genaue Modules-Admin-UI (minimal, reuse `features/extensions`).
- Icon-String→lucide-Komponente-Resolver im Frontend.
