# Plan: Lokale ComfyUI- und Cloud-Medienmodelle umschalten

## Ziel

Die globale LLM-Einstellung und Atelier erlauben eine eindeutige Auswahl
zwischen Cloud-Modellen und lokalen ComfyUI-Workflows für Bild und Video. Die
kanonische Modell-ID bleibt die einzige gespeicherte Routing-Quelle.

## Dateien

### HydraHive Core

- `core/src/hydrahive/llm/video_backends/_registry.py` — Kategorie eines
  aufgelösten lokalen Workflows prüfen.
- `core/src/hydrahive/tools/generate_image.py` — lokalen Bild-Workflow vor dem
  Run auf Kategorie `image` validieren.
- `core/src/hydrahive/tools/generate_video.py` — lokalen Video-Workflow vor dem
  Run auf Kategorie `video` validieren.
- `core/tests/test_generate_image.py` — Default-/Explizit-Routing und
  Kategoriefehler testen.
- `core/tests/test_generate_video.py` — Default-/Explizit-Routing und
  Kategoriefehler testen.
- `core/tests/test_llm_media_models_endpoint.py` — lokale Modellliste und
  Default-Contract prüfen.
- `frontend/src/features/llm/DefaultModelsSection.tsx` — Media-Picker für Bild
  und Video statt allgemeinem Registry-Picker.
- `frontend/src/features/llm/api.ts` — Media-Modelllisten typisiert abrufen.
- `frontend/src/features/llm/MediaModelSelect.tsx` — co-lokierter, nach
  Cloud/Lokal gruppierter Picker.
- `frontend/src/features/llm/*.test.tsx` (oder bestehende Teststruktur) —
  Gruppierung und gespeicherte lokale ID prüfen.

### Atelier-Modul

- `atelier/frontend/GeneratePanel.tsx` — Bildauswahl nach Cloud/Lokal
  gruppieren und Quellenkennzeichnung anzeigen.
- `atelier/frontend/VideoGenerationDialog.tsx` — bestehende Video-Gruppierung
  in den gemeinsamen UI-Helper überführen, eindeutige Quelle anzeigen.
- `atelier/frontend/MediaModelSelect.tsx` — gemeinsamer Atelier-Picker.
- `atelier/tests/...` — Bild-/Video-UI- und Backend-Routing-Regressionen.

## Implementierungsreihenfolge

### Task 1: Kategorien am lokalen Runner erzwingen

- [ ] Tests ergänzen: `local:.../image` wird im Video-Tool abgewiesen.
- [ ] Tests ergänzen: `local:.../video` wird im Bild-Tool abgewiesen.
- [ ] ROT ausführen.
- [ ] Gemeinsame Validierung im Registry-/Runner-Pfad implementieren; keine
      String-Heuristik, sondern Workflow-Metadaten verwenden.
- [ ] GREEN ausführen.
- [ ] Commit: `fix(media): validate local workflow category`.

### Task 2: Globale Bild-/Video-Defaults auswählbar machen

- [ ] API-Client und Tests für `GET /llm/media-models?category=...` ergänzen.
- [ ] ROT: lokales Modell ist in der Standardmodelle-Ansicht nicht vorhanden.
- [ ] `MediaModelSelect` co-lokiert implementieren: getrennte optgroups
      `Cloud / OpenRouter` und `Diese WKS / <Provider>`; gespeicherter Wert ist
      unverändert die Modell-ID.
- [ ] Bild und Video auf den neuen Picker umstellen; übrige Zwecke unverändert.
- [ ] GREEN: lokales Modell speichern, Reload zeigt denselben Wert.
- [ ] Commit: `feat(llm): select local media defaults`.

### Task 3: Atelier-Picker vereinheitlichen

- [ ] Bild- und Videomodelle mit lokalen und Cloud-Fakes testen.
- [ ] ROT: Bildliste besitzt keine Quellenkennzeichnung.
- [ ] Gemeinsamen Atelier-Picker bauen und in GeneratePanel sowie
      VideoGenerationDialog einsetzen.
- [ ] Modell-Metadaten weiter für Dauer, Aspect Ratio und Frame-Fähigkeiten
      nutzen.
- [ ] GREEN: beide Dialoge gruppieren gleich und senden die gewählte ID.
- [ ] Commit im Modulrepo: `feat(atelier): distinguish local media models`.

### Task 4: End-to-End- und Security-Verifikation

- [ ] Core- und Atelier-Testauswahlen sowie Lint/TypeScript-Build ausführen.
- [ ] Security-Review: model-ID nur aus serverseitig gelisteten Workflows,
      Kategorieprüfung, kein Cloud-Fallback.
- [ ] Auf WKS197 deployen.
- [ ] Mit UI: SDXL als Bilddefault setzen und Bild erzeugen; Wan als
      Videodefault setzen und Video erzeugen; anschließend Cloudmodell testen.
- [ ] Commits und PRs nach getrennten Repos erstellen.

## Akzeptanzkriterien

- [ ] Lokale und Cloud-Modelle sind bei Bild und Video eindeutig umschaltbar.
- [ ] Globale Defaults und Atelier-Einzelwahl benutzen dieselben IDs.
- [ ] Keine falsche Modellkategorie kann gestartet werden.
- [ ] Keine lokale Auswahl verlangt einen OpenRouter-Key.
- [ ] Cloud-Verhalten bleibt unverändert.

## Nicht in diesem Plan

- VRAM-Switching zwischen Ollama und ComfyUI.
- Zusätzliche Modelle/Workflows.
- Automatische Provider-Failover von lokal zu Cloud.
