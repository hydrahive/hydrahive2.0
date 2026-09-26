# Plan: Lokales Image-to-Video mit Start-/Endbild

## Ziel
Im Atelier soll neben dem lokalen Wan-Text-to-Video-Modell ein lokales Wan-FLF2V-Modell auswählbar sein. Mit einem Galerie-Startbild und optionalem Endbild soll ein Video erzeugt werden. Der bestehende Text-to-Video-Workflow bleibt unverändert.

## Dateien
- `installer/media-workflows/wan21-flf2v.json` — ComfyUI-API-Workflow mit Start-/Endbild-Platzhaltern.
- `installer/modules/72-local-media.sh` — lädt FLF2V-Checkpoint und CLIP-Vision-Modell und registriert den Workflow.
- `core/src/hydrahive/llm/video_backends/_base.py` — ergänzt einen optionalen Endframe-Parameter.
- `core/src/hydrahive/llm/video_backends/_comfyui.py` — lädt Data-URI-Frames in ComfyUI hoch und setzt die Bildnamen in den Graph ein.
- `core/tests/test_video_backends.py` — testet Upload und Start-/Endbild-Placeholder.
- `hydrahive2-modules/atelier/backend/video.py` — reicht beim lokalen Workflow das Endbild weiter.
- `hydrahive2-modules/atelier/tests/test_video_endframe.py` — Regressionstest für lokalen Endframe-Pfad.

## Implementierungsreihenfolge

### Task 1: Backend-Datenfluss
- [ ] Test für ComfyUI-Upload und beide Bild-Placeholder schreiben.
- [ ] Test muss zunächst fehlschlagen.
- [ ] `VideoParams.end_image_url` ergänzen.
- [ ] ComfyUI-Adapter implementiert Upload über `/upload/image` und ersetzt Start-/Endbild-Placeholder.
- [ ] Tests grün.

### Task 2: Atelier lokales Rendering
- [ ] Test erweitern, dass `end_source_rel` in `VideoParams` landet.
- [ ] Lokalen `render_clip`-Pfad erweitern.
- [ ] Tests grün.

### Task 3: Workflow und Installation
- [ ] FLF2V-API-Graph mit `WanFirstLastFrameToVideo`, `LoadImage`, `CLIPVisionLoader` und `CLIPVisionEncode` anlegen.
- [ ] Installer lädt FP8-FLF2V-Checkpoint und `clip_vision_h.safetensors` mit Prüfsummen.
- [ ] Workflow in `media_backends[].workflows` registrieren.
- [ ] Shell-Syntax und JSON validieren.

### Task 4: Integration
- [ ] Backend- und Modul-Tests ausführen.
- [ ] Frontend-Build ausführen.
- [ ] PRs mergen und WKS197 aktualisieren.
- [ ] Echten Start-/Endbild-Lauf mit niedriger Auflösung verifizieren.

## Akzeptanzkriterien
- [ ] Im Modellpicker erscheint `Wan 2.1 FLF2V 14B (lokal)`.
- [ ] Der Endbild-Picker wird nur bei einem Modell mit `last_frame` angezeigt.
- [ ] Start- und Endbild werden an ComfyUI übertragen und im Workflow eingesetzt.
- [ ] Der bisherige lokale T2V-Workflow bleibt verfügbar.
- [ ] Ein echter lokaler FLF2V-Test erzeugt ein Video.

## Nicht in diesem Plan
- Keine Änderung am OpenRouter-/Cloud-Modellkatalog.
- Keine automatische Auswahl des teuersten oder langsamsten Video-Modells.
- Keine neue Video-Editing-Funktion; Schnitt bleibt unverändert.
