# Videoschnitt — Export-Historie „Fertige Filme"

## Was
Exportierte Filme werden dauerhaft gelistet und sind jederzeit erneut
herunterladbar — in einer eigenen Box **„Fertige Filme"** unter der
Clip-Bibliothek. Bisher gab es nur einen flüchtigen Download-Link, der nach
Reload verschwand.

## Warum
Ein Export ist Arbeit (FFmpeg-Render). Das Ergebnis darf nicht verloren gehen,
nur weil man die Seite neu lädt. Eine persistente Liste macht die Exporte
wiederauffindbar, vergleichbar und löschbar.

## Wie
### Backend
- **Eindeutiger Dateiname:** Export schreibt `exports/schnitt-<YYYYMMDD-HHMMSS>.mp4`
  statt immer `exports/timeline.mp4` zu überschreiben → Historie bleibt erhalten.
- **Sidecar-Meta:** je Export eine `…​.json` mit `{created_at, duration}`.
- **`media_export.list_exports(project_id, media_slug)`**: liest den
  `exports/`-Ordner, liefert je MP4 `{name, rel_path, path, size, created_at,
  duration}` (created_at/duration aus Sidecar, Fallback mtime/None), neueste zuerst.
- **`media_export.delete_export(project_id, media_slug, name)`**: löscht MP4 +
  Sidecar. `name` wird gegen Path-Traversal validiert (nur Basename, muss im
  exports/-Ordner liegen).
- **Routen** (media_workspace.py Router):
  - `GET  /timeline/exports` → Liste
  - `DELETE /timeline/exports/{name}` → löschen
- Output liegt weiter unter `data_dir/workspaces` → Download via `/api/files`.

### Frontend
- `mediaWorkspaceApi.listExports` + `deleteExport` + Typ `MediaExportEntry`.
- **`ExportLibrary`-Box** unter der Bibliothek (rechte Spalte): Liste der Exporte
  mit Name, Dauer, Größe, Zeit; je Eintrag Download (`fileUrl(path)`) + Löschen.
- `useCutExport` lädt die Liste initial und nach jedem erfolgreichen Export neu.
- `ExportBar` behält den frischen Direkt-Link, die Box ist die persistente Sicht.

## Akzeptanzkriterien
- [ ] Jeder Export erzeugt eine eigene Datei (überschreibt keine ältere).
- [ ] „Fertige Filme"-Box listet alle Exporte, neueste zuerst, überlebt Reload.
- [ ] Download je Eintrag funktioniert; Löschen entfernt Datei + Sidecar.
- [ ] Nach einem Export erscheint der neue Film sofort in der Box.
- [ ] Backend-Tests grün; Build/Typecheck/ESLint grün.
