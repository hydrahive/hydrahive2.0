# Plan: Media-Produktionssuite Punkte 1–6

## Ziel

Das Media-Cockpit wird zu einem projektgebundenen Produktionssystem mit persistenten und projektübergreifenden Asset-Referenzen, echten Arbeitsflächen, Akt/Szene/Shot-Regie, kontextgebundenem Media-Agent und persistentem Mehrspur-Schnitt samt bewusst ausgelöstem Export.

## Architekturentscheidungen

- Alle Produktionsdaten bleiben dateibasiert unter `media/<slug>/` und damit Samba-/Git-lesbar.
- Cross-Projekt-Assets sind JSON-Referenzen, niemals Symlinks. Jeder Lese-/Kopiervorgang prüft den aktuellen Zugriff auf Heimat- und Quellprojekt.
- Kopieren ist explizit und schreibt eine unabhängige Datei nach `assets/imported/`.
- Regie liegt in `screenplay.json`; Timeline in `timeline/timeline.json`; Agent-Kontext in `agent/context.json`.
- Der Media-Agent speichert lokalen Kontext und öffnet für echte LLM-Kommunikation bewusst Buddy; er startet keine Generierung.
- Schnitt verwendet ein eigenes React-Timeline-Modell. Export wird serverseitig mit einer Argumentliste an FFmpeg übergeben, nie über eine Shell. Nur validierte, aufgelöste Workspace-Dateien sind erlaubt.

## Implementierungsreihenfolge

### 1. Persistente und Cross-Projekt-Asset-Referenzen
- Store und CRUD-/Import-API mit Pfad- und Berechtigungsprüfung.
- Tests für CRUD, Traversal, fremde Projekte, verlorenen Zugriff und Kopie.
- Cockpit-Auswahl und Referenzansicht.

### 2. Arbeitsflächen
- Gemeinsamer nicht versehentlich schließbarer Workspace-Rahmen.
- Bearbeitung/Navigation für Charakter, CI, Bild, Audio, Video, Regie und Asset-Zuordnung.
- Speichern explizit; kein Outside-/Escape-Close.

### 3. Regie Akt → Szene → Shot
- Dateimodell und CRUD-/Reorder-API.
- Editor für Filmkopf, Akte, Szenen und Shots.
- Prompt-/Asset-Verknüpfungen; keine Batch-Generierung ohne separates Gate.

### 4. Media-Agent
- Persistenter Kontext pro Media-Projekt.
- Minimierbares Popup mit Notizen/Auftrag und bewusstem Übergang zu Buddy.
- Keine automatische LLM- oder Medienaktion.

### 5. Mehrspur-Schnitt
- Timeline-Modell für Video, Voice, Musik und Audio.
- Clip-Operationen: hinzufügen, verschieben, trimmen, splitten, löschen; Undo/Redo im Frontend.
- Preview der abspielbaren Einzelquelle am Playhead.
- Server-Persistenz und Exportjob mit FFmpeg.

### 6. Produktions-Gate
- Backendtests, Frontend-Build, Offline-Guard, Security- und HH-Review.
- PR und Merge nach grünen Pflichtchecks.

## Akzeptanzkriterien

- Referenzen bleiben nach Reload erhalten und zeigen Herkunft/Read-only/Verfügbarkeit.
- Fremdprojektzugriff wird bei jeder Operation erneut geprüft.
- Regie und Timeline sind vollständig dateibasiert und wieder ladbar.
- Kein normaler Klick startet LLM, Generierung oder Rendering.
- Export erfordert eine ausdrückliche Aktion und akzeptiert keine Pfade außerhalb zugänglicher Workspaces.
- Build, relevante Tests und Offline-Guard sind grün.
