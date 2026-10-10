# /api/files – Zugriff nur auf eigene bzw. freigegebene Dateien

Stand 10.10.2026 · Issue #538 (security, p1) · gemeldet aus dem HydraVR-Projekt.

## Befund
`GET /api/files?path=…` lieferte jedem angemeldeten Nutzer jede Datei unter `data_dir/workspaces` (alle Projekte,
Master- und Spezialisten-Workspaces) und unter `/tmp`. Geprüft wurden nur Login, ein absoluter Pfad und die
erlaubten Wurzeln. Nachweis: Ein Nutzer ohne Mitgliedschaft las eine Atelier-Datei eines fremden Projekts (200).

## Regel (auf dem aufgelösten Pfad – Symlinks und `..` zählen nicht)
| Pfad | Erlaubt |
|---|---|
| `workspaces/projects/<pid>/…` | Mitglied mit Rolle ≥ read (wie die Projekt-Routen), System-Admin |
| `workspaces/master/<aid>/…` | Besitzer (`owner`), System-Admin |
| `workspaces/specialists/<aid>/…` | Besitzer; gehört der Spezialist zu einem Projekt (`project_id`), auch dessen Mitglieder; System-Admin |
| übrige Dateien unter `workspaces/` | nur System-Admin |
| `HH_MEDIA_DIRS` | alle Angemeldeten (vom Admin bewusst freigegeben) – unverändert |
| übriges `data_dir` (sessions.db, Konfiguration) | niemand – auch wenn `data_dir` unter `/tmp` liegt |
| `/tmp` | nur System-Admin |

- Unbekanntes Projekt bzw. unbekannter Agent (oder Agent im falschen Ordner) → 404, sonst 403.
- Gilt für Bearer-Header und `?token=` gleich.

## /tmp
Auf Prod läuft der Dienst mit `PrivateTmp=yes`; KI-Ausgaben liegen im Workspace (`generate_image` u. a. →
`ctx.workspace/generated`). Medien unter `/tmp` erscheinen im Verlauf nur aus Tests und Werkzeug-Ausgaben, und nur bei
System-Admins (till/admin, 79 Nachrichten seit Juli). Daher: `/tmp` nur noch für System-Admins – kein eigener
Ordner je Nutzer nötig. Werkzeuge, die für normale Nutzer Medien zeigen sollen, speichern im Workspace.

## Nicht hier
`?token=` (voller JWT in Bild-Links) durch eine kurzlebige, pfadgebundene Signatur ersetzen – eigener Schritt.

## Code
`core/src/hydrahive/api/routes/_files_access.py` (`check_read`), aufgerufen in `files.get_file` nach der
Wurzel-Prüfung. Tests: `core/tests/test_files_access.py`.
