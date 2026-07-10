# Plan: Media-Cockpit mit Leben füllen

## Ziel
Das Media-Cockpit wird vom Mockup-Gerüst zu einem echten, offline-first Produktionsarbeitsplatz. Es liest vorhandene Atelier-/Projekt-Daten, bereitet Generator-Aufträge bewusst vor und startet keine automatischen LLM- oder Medienjobs.

## Bestehende Datenquellen
- `chatApi.listProjects()` — HydraHive-Projekte für Projektbindung.
- `atelierApi.getCI(projectId)` — Stil/CI und Default-Bildmodell.
- `atelierApi.listCharacters(projectId)` — Charaktere und Referenzen.
- `atelierApi.gallery(projectId)` — Bilder/Keyframes mit Prompt/Modell/Seed.
- `atelierApi.listVideos(projectId)` — Videojobs/Clips.
- `atelierApi.listFilms(projectId)` — Filmjobs/Exports.
- `atelierApi.presets()` — verfügbare Regie-/Kamera-Presets.

## Reihenfolge

### Task 1: Atelier-Daten lesen und leere Zustände zeigen
- [x] Media-Cockpit lädt für das gebundene Projekt CI, Charaktere, Galerie, Videos, Filme und Presets.
- [x] Fehler pro Datenquelle werden als lokale/offline Hinweise gezeigt; die Seite bleibt nutzbar.
- [x] Keine Generierung, kein LLM, kein automatischer Schreibzugriff.
- Commit: `feat(cockpit): load atelier media data`

### Task 2: Asset-Bibliothek echt befüllen
- [x] Rechte Asset-Bibliothek zeigt echte Charaktere, CI/Stil, Galerie-Keyframes und Audio/Video-Hinweise.
- [x] Asset-Klicks öffnen Atelier/Music/Videoeditor statt Jobs zu starten.
- [ ] Wenn keine Daten vorhanden sind: klare Empty States mit nächstem Schritt.
- Commit: `feat(cockpit): bind media asset library`

### Task 3: Szenen-/Generatorbereich mit Daten vorbereiten
- [x] Szenenliste nutzt vorhandene Szenen-Quelle, falls vorhanden; solange keine API existiert, werden Galerie/Video-Prompts als Produktionsslots angezeigt.
- [x] Auswahl einer Szene/eines Slots setzt den Generator-Auftrag lokal.
- [x] Auftrag bleibt Draft im Cockpit; Button öffnet bewusst Atelier.
- Commit: `feat(cockpit): prepare media generator drafts`

### Task 4: Timeline aus echten Jobs ableiten
- [x] Timeline zeigt Videojobs/Filmjobs aus Atelier statt Demo-Clips.
- [x] Statusfarben: pending/processing/completed/failed.
- [x] Keine Polling-Spam-Schleife; Refresh per User-Aktion oder sparsamer Reload.
- Commit: `feat(cockpit): derive media timeline from jobs`

### Task 5: Modelle/Presets besser anbinden
- [x] Modellfelder übernehmen CI-Default und bekannte Video/Musik-Defaults.
- [x] Presets werden als auswählbare Tags/Pills im Generator-Auftrag angeboten.
- [x] Nicht unterstützte Modelllisten bleiben als statische Defaults sichtbar.
- Commit: `feat(cockpit): bind media model presets`

## Akzeptanzkriterien
- [ ] `/media` zeigt echte Projekt-/Atelierdaten, wenn vorhanden.
- [ ] `/media` ist ohne Internet/LLM weiter nutzbar.
- [ ] Normale Klicks starten keine LLM- oder Mediengenerierung.
- [ ] Die Mockup-Struktur bleibt erhalten.
- [ ] Build und `check:cockpit-offline` sind grün.

## Nicht in diesem Plan
- Kein automatisches Rendern/Generieren.
- Kein vollständiger Schnitt-Editor im Cockpit.
- Kein neuer Backend-Szenen-Endpunkt, solange eine vorhandene Quelle reicht.
