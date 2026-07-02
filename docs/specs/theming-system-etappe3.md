# Theme-System Etappe 3 — Hub-Installer (WordPress-Gefühl)

Status: FREIGEGEBEN (Weg A — eigenes Git-Hub-Repo, wie Module).
Baut auf Etappe 1 (PR #245) + Etappe 2 (PR #246) auf.

## Problem

Themes sind heute Dropin-Ordner (`frontend/src/themes/<id>/`), die man manuell
ins Repo legen muss. Ein Admin ohne Shell-Zugriff kann kein Theme installieren.
Etappe 3 macht Themes über einen **Hub installierbar** — Admin sieht
„Installiert / Verfügbar", ein Klick installiert/entfernt.

## Blaupause: das Modulsystem (1:1 spiegeln)

`core/src/hydrahive/modules/` + `api/routes/modules.py` + `features/modules/` +
Git-Hub-Repo `hydrahive2-modules`. Themes bekommen dieselbe Struktur, aber
**schlanker**, weil ein Theme reines Frontend ist:

| Modul | Theme |
|-------|-------|
| Backend + Migrations + Frontend | **nur Frontend** |
| 2 Kopierziele (modules_dir + frontend) | **1 Ziel** (`frontend/src/themes/<id>`) |
| install.sh/uninstall.sh Service | **keine** |
| DB-Tabellen, Agent-Tools | **keine** |
| Registry lädt Python-Manifest | Registry liest nur `theme.json` |

## Architektur

### Git-Hub-Repo `hydrahive2-themes`
```
hub.json                 # { "themes": [ { "id", "name", "path" } ] }
aurora/                  # ein Theme = ein Ordner (wie im Frontend-Paket)
  theme.json
  theme.css
  preview.jpg (optional)
  layout.tsx  (optional)
```

### Settings (`settings/_paths.py`) — additiv
- `themes_hub_cache` = `data_dir/.theme-cache/hub`
- `theme_hub_git_url` = `HH_THEME_HUB_GIT_URL` (Default GitHub `hydrahive2-themes`)
- `theme_hub_extra_git_urls` = `HH_THEME_HUB_GIT_URLS` (Multi-Hub, wie Module)
- Kopierziel = `base_dir/frontend/src/themes/<id>` (kein eigenes data_dir nötig)

### Backend `core/src/hydrahive/themes/`
- `hub_client.py` — **direkte Spiegelung** des Modul-hub_clients (klonen/pullen,
  Multi-Hub-Merge, `read_hub_index()` → `{"themes": [...]}`, `theme_source_path()`).
- `installer.py` — schlank:
  - `copy_theme_in(id)` → kopiert Hub-Cache-Ordner nach `frontend/src/themes/<id>`
  - `remove_theme_files(id)` → löscht den Ordner (aurora ist geschützt: nie löschbar)
  - `install/uninstall(id)` Generatoren: kopieren → `npm run build` → Restart-Request
  - **kein** Service-Script, **kein** modules_dir
- `manifest.py` — `ThemeManifest.load()` (id/name/version + layout/variables),
  Validierung `^[a-z0-9][a-z0-9-]*$`.
- `registry.py` — listet installierte Themes durch Scan von `frontend/src/themes/*/theme.json`.

### API `api/routes/themes.py`
`/api/admin/themes` (require_admin), spiegelt modules.py:
- `GET ""` → `{ installed, available }`
- `POST /{id}/install` (SSE-Stream)
- `POST /{id}/update` (SSE-Stream)
- `DELETE /{id}` (SSE-Stream)
Registriert in `api/main.py`.

### Frontend `features/themes/`
Spiegelt `features/modules/`:
- `api.ts`, `types.ts`, `ThemesPage.tsx`, `ThemeAdminCard.tsx`
- Settings-Registry-Eintrag `{ id: "themes", route: "/themes", adminOnly: true }`
- Route in `App.tsx` unter `AdminGuard`

## Schutz & Sicherheit
- `aurora` + eingebaute Themes (`standard`/`sidebar`) sind **nicht deinstallierbar**
  (Backend lehnt ab; UI zeigt keinen Entfernen-Button).
- Theme-`id` streng validiert (kein Pfad-Escape, `theme_source_path` prüft
  Verzeichnisgrenze wie beim Modul-hub_client).
- `symlinks=False` beim Kopieren (kein Escape-Vektor).
- User-CSS ist reines CSS (kein JS). `layout.tsx` aus Hub = gleiche Vertrauensstufe
  wie ein Modul (Admin-Aktion, Katalog kuratiert).

## .gitignore
```
src/themes/*/            # Hub-installierte Themes ignorieren
!src/themes/aurora/      # Beispiel-Theme bleibt getrackt (Vorlage)
src/themes/index.generated.ts
```
(aurora ist bereits im Index → bleibt ohnehin getrackt; Negation für Robustheit.)

## Akzeptanzkriterien
1. `hydrahive2-themes`-Repo existiert mit `hub.json` + aurora.
2. Admin-Seite „Themes" listet Installiert + Verfügbar.
3. Ein Klick „Installieren" auf ein Hub-Theme → landet in `frontend/src/themes/<id>`,
   Build läuft, nach Restart im Profil-Picker wählbar.
4. Deinstallieren entfernt den Ordner (aurora/standard/sidebar geschützt).
5. Backend-Tests grün (manifest/hub_client/installer), `npm run build` + `tsc` grün.

## Nicht in diesem Feature
- ZIP-Upload (Weg B) — später additiv möglich.
- Theme-Editor im UI.
- Pro-Theme-Versionsvergleich/Changelog.
