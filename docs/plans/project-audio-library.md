# Plan: Projektgebundene Audio-Bibliothek

## Ziel

Musicplayer-Tracks liegen updatefest im Projektworkspace, folgen Projekt-RBAC und können pro Track heruntergeladen werden.

## Dateien

### Core
- `core/src/hydrahive/modules/manifest.py` — validierter `persistent_paths`-Vertrag.
- `core/src/hydrahive/modules/installer.py` — sichere Stash-/Restore-Ersetzung.
- `core/tests/test_module_manifest.py` — Pattern-Validierung.
- `core/tests/test_module_installer.py` — Persistenz, Konflikte und Symlink-Grenzen.
- `core/tests/test_module_install_flow.py` — Update-Orchestrierung ohne vorzeitiges Löschen.

### Musicplayer-Modul
- `musicplayer/migrations/003_project_scope.sql` — `project_id`, Backfill und Indizes.
- `musicplayer/backend/storage.py` — `media/audio` im Projektworkspace und Legacy-Migration.
- `musicplayer/backend/tracks_store.py` — projektgefilterte Metadatenzugriffe.
- `musicplayer/backend/routes.py` — Projekt-RBAC, Stream und Download.
- `musicplayer/backend/import_routes.py` — projektlokaler Generated-Import.
- `musicplayer/backend/__init__.py` — aktualisierte Moduldokumentation.
- `musicplayer/frontend/api.ts` — projektgebundene Requests und Download-URL.
- `musicplayer/frontend/types.ts` — Bibliotheks-/Rechte-Typen.
- `musicplayer/frontend/MusicPlayerBuddyBox.tsx` — Projektzustand und Reset.
- `musicplayer/frontend/MusicPlayerProjectView.tsx` — Bibliothek, Rechte und Download-Button.
- `musicplayer/frontend/index.tsx` — zusätzliche Übersetzungen.
- `musicplayer/tests/*` — Storage-, API-, RBAC-, Migrations- und Frontend-Verträge.
- `musicplayer/manifest.json`, `README*` — Version und Persistenzdeklaration.

## Implementierungsreihenfolge

### Task 1: Core-Persistenzvertrag
- [x] Tests für gültige/ungültige `persistent_paths` schreiben und rot ausführen.
- [x] Installer-Test für Erhalt deklarierter Dateien und Ablehnung von Symlinks/Kollisionen schreiben.
- [x] Manifest-Validierung und sichere Stash-/Restore-Logik implementieren.
- [x] Update-Flow auf atomaren Dateiersatz ohne vorzeitiges `remove_module_files` umstellen.
- [x] Core-Tests grün ausführen.

### Task 2: Projekt-Datenmodell und Storage
- [x] Migrationstest für `project_id` und source-basierten Backfill schreiben.
- [x] Storage-Tests für Projektpfad, Traversal-Grenzen und Legacy-Kopie schreiben.
- [x] Migration 003, projektgebundenen Track-Store und Storage implementieren.
- [x] Vorhandene Dateien werden nur nach erfolgreicher Zielprüfung aus Legacy entfernt.

### Task 3: Projekt-RBAC und Download
- [x] API-Tests für unauthenticated, fremdes Projekt, read/write/admin schreiben.
- [x] Tests für projektfremde Track-ID und Download-Disposition schreiben.
- [x] Projektgebundene Listen-, Upload-, Stream-, Download-, Delete- und Import-Routen implementieren.
- [x] Alle Backendtests grün ausführen.

### Task 4: Frontend
- [x] Frontend-Vertrag für projectId, leeren Zustand, Rechte und Download-Button schreiben.
- [x] API-Client und Typen projektgebunden umstellen.
- [x] Player in keyed Project-View aufteilen, damit Projektwechsel Audiozustand beendet.
- [x] Upload/Import/Delete nach effektiven Rechten darstellen.
- [x] Download-Button pro Track ergänzen.
- [x] TypeScript-Build, ESLint und Offline-Guard grün ausführen.

### Task 5: Migration und Veröffentlichung
- [ ] Security- und HH2-Strukturreview durchführen.
- [ ] Core committen/pushen und zuerst deployen.
- [ ] Modul committen/pushen und danach aktualisieren.
- [ ] Vorhandene Tracks kopieren und Zielgrößen prüfen, dann Legacy-Dateien entfernen.
- [ ] Alle Streams und mindestens einen Download lokal prüfen.
- [ ] Musicplayer zweimal nacheinander aktualisieren und Dateibestand erneut prüfen.

## Nicht enthalten

- Videoformate, Transcoding, globale Bibliothek oder projektübergreifende Freigaben.
