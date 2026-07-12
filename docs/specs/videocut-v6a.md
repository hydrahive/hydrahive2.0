# Videoschnitt V6a — WYSIWYG-Export entlang der Schnittpunkte + Download

## Was
Der fertige Schnitt wird als MP4 gerendert — **so wie er in der Preview aussieht**:
Der Output wird entlang der Schnittpunkte assembliert (Toggle vid1↔vid2 mit
Fallback bei Lücken), nicht mehr als stumpfes Layer-Overlay. Im Schnittpult gibt
es einen **„Film exportieren"**-Button mit Fortschritt und **Download-Link**.

## Warum
Bisher ignorierte `media_export.py` die `cut_points` komplett (altes
„vid2 überdeckt vid1"-Modell) → der Export zeigte nicht das, was man sieht. Und
es gab keinen UI-Weg zum Rendern/Herunterladen. V6a schließt beide Lücken.

## Scope-Grenze
- Übergangseffekte (Crossfade/Wipe/Fade) werden in V6a als **Hartschnitt**
  gerendert. Weiche Übergänge im Renderer kommen in V6b (FFmpeg `xfade`).

## Wie
### Assemblierung (neu, rein & testbar): `media_timeline_assembly.py`
- `video_onair_segments(timeline) -> dict[clip_id, list[(start, end)]]`:
  Zerlegt die Zeitachse an allen Ereigniszeitpunkten (0, Ende, alle
  Schnittpunkt-Zeiten, alle Video-Clip-Kanten). Für jedes Elementar-Intervall
  wird am Mittelpunkt die aktive Spur bestimmt (Anzahl Schnittpunkte ≤ t: gerade
  → vid1, ungerade → vid2) und der dort sichtbare Clip gesucht — mit **Fallback**
  auf die andere Video-Spur bei Lücke. Ergebnis: je Clip die disjunkten
  Intervalle, in denen er „on air" ist. Exakt dieselbe Logik wie das Frontend
  (`assembleOutput.activeVideoAt`).

### Export: `media_export.py`
- Nutzt `video_onair_segments`. Für jeden Video-Clip mit on-air-Intervallen ein
  Overlay, dessen `enable`-Ausdruck die Vereinigung der on-air-Intervalle ist
  (`between(t,a1,b1)+between(t,a2,b2)+…`). Dadurch ist zu jedem Zeitpunkt genau
  ein Video-Clip sichtbar → deterministisch, WYSIWYG.
- Audio-Spuren (music/fx/voice) werden wie bisher gemischt.
- **Video-Ton der on-air-Segmente** wird mitgenommen, sofern die Quelldatei eine
  Audiospur hat (einmalige `ffprobe`-Prüfung je Datei; stumme Videos werden
  übersprungen, kein Crash).
- Output bleibt `…/media/<slug>/exports/timeline.mp4`; liegt unter
  `data_dir/workspaces` → per `/api/files` downloadbar.

### Frontend
- `MediaPostProduction`: Button **„Film exportieren"** → ruft
  `mediaWorkspaceApi.exportTimeline` → zeigt „Rendere…" → bei Erfolg
  **Download-Link** (`fileUrl(result.path)`, `download`-Attribut). Fehler inline.
- Kleiner Hook/Helper hält den Export-Status (`idle|running|done|error`).

## Akzeptanzkriterien
- [ ] Export rendert den Schnitt entlang der Schnittpunkte (Toggle + Fallback).
- [ ] Button zeigt Fortschritt und liefert einen funktionierenden Download-Link.
- [ ] Video-Ton der on-air-Segmente ist im Export hörbar (falls vorhanden),
      Audio-Spuren gemischt.
- [ ] Übergänge werden (vorerst) als Hartschnitt gerendert.
- [ ] Backend-Test: Export mit Schnittpunkten erzeugt eine valide Datei.
- [ ] Backend-Tests + Build/Typecheck/ESLint grün.
