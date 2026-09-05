# Plan: Local Media Runtime P1 — Routing

## Ziel

Lokale `local:<backend>/<model>`-IDs funktionieren als Standardmodelle und werden in Core-Agententools sowie im Atelier tatsächlich über die bestehende Backend-Registry ausgeführt, statt versehentlich an OpenRouter zu gehen.

## Repositories und Dateien

### Core (`hydrahive2`)

- `core/src/hydrahive/llm/video_backends/_runner.py` — gemeinsamer submit/poll/fetch-Lauf.
- `core/src/hydrahive/tools/generate_video.py` — effektives Standardmodell vor Providerprüfung auflösen.
- `core/src/hydrahive/tools/generate_image.py` — lokales Bildrouting und lokale Resultate.
- `core/tests/test_local_media_runner.py` — Runner-Zustände, Timeout und Ergebnis.
- `core/tests/test_generate_video.py` — lokales Standardmodell.
- `core/tests/test_generate_image.py` — lokales Bildmodell ohne OpenRouter-Key.

### Atelier (`hydrahive2-modules`)

- `atelier/backend/local_media.py` — schmale Brücke zur Core-Registry und Speicherung.
- `atelier/backend/generate.py` / `service.py` — lokaler Bildpfad async.
- `atelier/backend/video.py` — lokale Videojobs über Core-Runner.
- `atelier/backend/routes.py` / Aufrufer — async-Kaskade für Bildgenerierung.
- zugehörige Atelier-Tests — lokale Bild-/Videojobs und Cloud-Regression.
- `atelier/manifest.json` — Modulversion erhöhen.

## Implementierungsreihenfolge

### Task 1: Gemeinsamer Core-Runner

- [ ] Tests für done/error/timeout und Resultatpfad schreiben.
- [ ] Tests rot ausführen.
- [ ] `_runner.py` mit `run_local_media(...)` implementieren.
- [ ] Tests grün ausführen.
- [ ] Refactor ohne Verhaltensänderung.
- [ ] Commit im Core-Repo.

### Task 2: Core-Agententools

- [ ] Regressionstest: lokales Standard-Videomodell braucht keinen OpenRouter-Key.
- [ ] Regressionstest: lokales Bildmodell nutzt Registry und liefert gespeicherten Pfad.
- [ ] Tests rot ausführen.
- [ ] effektives Modell jeweils vor Key-/Providerentscheidung auflösen.
- [ ] lokale Referenzbilder sicher als data-URI übergeben.
- [ ] Tests grün ausführen.
- [ ] Commit im Core-Repo.

### Task 3: Atelier-Bildrouting

- [ ] Test: `local:`-Bildmodell nutzt Core-Runner und speichert Galerie-Metadaten.
- [ ] Test: OpenRouter-Pfad bleibt unverändert.
- [ ] Tests rot ausführen.
- [ ] Bild-Service/Aufrufer kontrolliert async machen.
- [ ] lokales Resultat in vorhandenen Galeriepfad übernehmen.
- [ ] Tests grün ausführen.
- [ ] Modulversion erhöhen und Commit im Modul-Repo.

### Task 4: Atelier-Videorouting

- [ ] Test: lokaler Videojob nutzt Core-Runner ohne OpenRouter-Key.
- [ ] Test: Fehlerstatus wird in Jobdatei geschrieben.
- [ ] Test: Cloud-Video bleibt unverändert.
- [ ] Tests rot ausführen.
- [ ] `render_clip` anhand des effektiven Modells routen.
- [ ] Resultat in bestehenden Video-Store übernehmen.
- [ ] Tests grün ausführen.
- [ ] Commit im Modul-Repo.

### Task 5: Integration

- [ ] Core-Gesamttests und Ruff.
- [ ] Atelier-Gesamttests und ESLint/TypeScript über installierten Modulbuild.
- [ ] `local:`-Bild und `local:`-Video gegen Mock-Worker E2E.
- [ ] Security-Review: SSRF, Pfade, Größen, Fehlertexte.
- [ ] getrennte PRs für Core und Modul; Modul-PR nennt Core-Voraussetzung.

## Akzeptanzkriterien

- [ ] Kein lokales Modell wird an OpenRouter gesendet.
- [ ] Lokale Standardmodelle funktionieren ohne OpenRouter-Key.
- [ ] Nicht konfigurierte/offline lokale Backends fallen nicht still auf Cloud zurück.
- [ ] Core und Atelier verwenden denselben Adapter und dieselben Modell-IDs.
- [ ] Bestehende OpenRouter-Tests bleiben grün.
- [ ] Resultatpfade bleiben unter dem jeweiligen Workspace/Atelier-Projekt.

## Nicht in P1

- Installation von ComfyUI oder GPU-Treibern.
- Media-Worker-Pairing und automatische Node-Registrierung.
- Download großer Modelle.
- VRAM-Switching mit Ollama.
- Realer WKS-Render; folgt nach P2/P3 im Pilot P4.
