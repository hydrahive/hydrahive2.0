# Media UX P2.1: Asset-Picker und vollständige Shot-Bearbeitung

## Ziel

Der Regieeditor bearbeitet alle bereits persistierten Shot-Felder und ersetzt manuelle ID-Eingaben durch visuelle Mehrfachauswahl aus den persistenten Media-Asset-Referenzen.

## Dateien

- `frontend/src/features/cockpit/MediaScreenplayOverlay.tsx` — lädt Drehbuch und Referenzen, verwaltet Akte/Szenen/Shots.
- `frontend/src/features/cockpit/media/MediaShotEditor.tsx` — vollständiges Shot-Formular.
- `frontend/src/features/cockpit/media/MediaAssetPicker.tsx` — visuelle, typgefilterte Mehrfachauswahl.
- `frontend/src/features/cockpit/media/shotUpdates.ts` — immutable Shot-Updates und normalisierte Auswahl.
- `frontend/src/features/cockpit/media/shotUpdates.test.ts` — Update- und Auswahltests.

## Implementierungsreihenfolge

1. Pure Update-Helfer mit Tests für Feldänderung, Asset-Toggle und Charakter-/Asset-Trennung erstellen.
2. Visuellen Picker für persistente Referenzen erstellen; nicht verfügbare Einträge deaktivieren.
3. Vollständigen Shot-Editor für Titel, Beschreibung, Dauer, Kamera, Charaktere, Assets und Dialog erstellen.
4. Regieoverlay auf Komponenten aufteilen und bestehende Screenplay-API unverändert nutzen.
5. Tests, Build, Offline-Guard und Architekturprüfung ausführen.

## Akzeptanzkriterien

- Alle Shot-Felder sind editierbar und werden über die bestehende Screenplay-API gespeichert.
- Dauer ist auf 0,1 bis 3600 Sekunden begrenzt.
- Charaktere werden aus Referenzen vom Typ `character` gewählt.
- Allgemeine Assets schließen Charakterreferenzen aus.
- Nicht verfügbare Referenzen bleiben sichtbar, sind aber nicht neu auswählbar.
- Bereits ausgewählte, später nicht verfügbare IDs gehen beim Bearbeiten nicht still verloren.
- Es gibt keine manuelle Asset-ID-Eingabe und keine Generierung.

## Nicht enthalten

- Generatorstart oder Batch-Generierung.
- Timeline-Drag-and-drop oder Export.
- Neue Backend-Endpunkte oder Datenmigrationen.
