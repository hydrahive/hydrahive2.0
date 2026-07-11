# Plan: Media-Projekt-Datenmodell und Workspace-Struktur

## Ziel
Media-Projekte werden innerhalb eines zugänglichen HydraHive-Heimatprojekts dateibasiert und offline-first verwaltet. Die API erstellt und pflegt sichere Workspace-Strukturen; das Media-Cockpit zeigt echte Einträge statt Demo-Projekte.

## Dateien
- `core/src/hydrahive/media_projects.py` — Validierung, sichere dateibasierte CRUD-Operationen und Verzeichnisstruktur.
- `core/src/hydrahive/api/routes/media_projects.py` — authentifizierte projektgebundene REST-Endpunkte.
- `core/src/hydrahive/api/main.py` — Router-Registrierung.
- `core/tests/test_media_projects_api.py` — CRUD, Zugriff, Traversal und Workspace-Struktur.
- `frontend/src/features/cockpit/mediaProjectsApi.ts` — typisierter API-Client.
- `frontend/src/features/cockpit/MediaCockpitPage.tsx` — echte Media-Projektliste und Anlegen-Dialog.

## Datenformat
`media/<slug>/media-project.json` enthält Version, Slug, Name, Beschreibung, Heimatprojekt-ID sowie Erstellungs- und Änderungszeit. `project.md` ist eine menschenlesbare Übersicht. Unterordner: `prompts`, `assets`, `images`, `video`, `audio`, `timeline`, `exports`.

## Implementierungsreihenfolge

### Task 1: Backend und Tests
- [ ] API-Tests für Create/List/Get/Patch/Delete sowie Zugriff und ungültige Slugs schreiben (RED).
- [ ] Dateibasierten Store mit atomarem JSON-Schreiben und sicherer Slug-Validierung implementieren.
- [ ] Projektzugriff vor jeder Operation prüfen.
- [ ] Tests grün ausführen (GREEN).

### Task 2: Cockpit-Anbindung
- [ ] Typisierten Client ergänzen.
- [ ] Demo-Dropdown durch echte projektabhängige Liste ersetzen.
- [ ] Geschützten Anlegen-Dialog ergänzen; kein Outside-/Escape-Close.
- [ ] Offline-/Leer-/Fehlerzustände anzeigen.

### Task 3: Verifikation
- [ ] Backendtests, Frontend-Build und Offline-Guard ausführen.
- [ ] Security- und Architektur-Review vor Commit.

## Akzeptanzkriterien
- [ ] Zugriffsberechtigte Nutzer können Media-Projekte CRUD-verwalten.
- [ ] Ein Create erzeugt die vollständige Workspace-Struktur.
- [ ] Traversal, ungültige Slugs und fremde Projekte werden abgewiesen.
- [ ] `/media` verwendet echte Media-Projekte und startet keinerlei LLM-/Generierungsjob.

## Nicht in diesem Plan
- Promptarchiv-Inhalte, Cross-Projekt-Assets, Rendering, Mediengenerierung, Timeline-Editor und Media-Agent.
