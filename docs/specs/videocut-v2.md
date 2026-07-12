# Videoschnitt V2 — Playback, Playhead & Transport

## Was
Der Videoschnitt bekommt eine funktionierende Vorschau: Der **Output-Monitor**
spielt die Timeline ab (clientseitig, kein Server-Render). Ein **Playhead** läuft
über den Spuren mit und ist per Klick/Scrub verschiebbar. Die **Transport-Buttons**
(Anfang/Play/Pause/Stopp/Ende) sind funktional, eine **Zeitanzeige** zeigt Position
und Gesamtlänge.

## Warum
Zweiter Slice der Videoschnitt-Roadmap (Task d778bcdb). V1 hat Bibliothek → Clip →
Spur → Persistenz geliefert; V2 macht das Ergebnis erlebbar, ohne auf Export (V6)
zu warten. Trim/Split kommt in V3.

## Wie
- **Backend: keine Änderungen.** Reine Frontend-Erweiterung auf den V1-Strukturen.
- **Master-Clock** (`useCutPlayback`): eine wall-clock-getriebene rAF-Schleife führt
  `currentTime` in Sekunden. Transport: `play/pause/stop/seek/toStart/toEnd`.
  `duration` = Ende des spätesten Clips über alle Spuren. Beim Erreichen des Endes
  stoppt die Wiedergabe.
- **Output-Monitor** (`OutputMonitor`): zeigt den aktiven visuellen Clip. Priorität
  **Video 2 über Video 1** (obere Spur gewinnt). Video-Clips → `<video>` (mit Ton),
  Bild-Clips → `<img>` (Standbild für ihre Dauer). Kein aktiver Clip → „kein Signal".
- **Audio parallel** (`PlaybackAudio`): je Audio-Spur (Musik/Effekt/Sprache) ein
  verstecktes `<audio>`-Element, das den aktiven Clip abspielt. `volume` je Clip,
  `muted` je Spur.
- **Grobe Sync** (`useMediaSync`): Media-Elemente folgen der Master-Clock. Bei Drift
  > 0,3 s wird `element.currentTime` nachgezogen; `play()/pause()` folgen dem
  Play-Status. Clip-Wechsel → Element-Remount via `key={clip.id}`. Für eine Preview
  ausreichend (kein frame-genauer Server-Sync).
- **Playhead** (`TrackArea`): vertikale Linie über Ruler + Spuren, Position aus
  `currentTime`. Der Ruler ist Scrub-Fläche: Pointer-Down/-Move setzt `currentTime`
  über `onSeek`.
- **URL-Auflösung**: Asset-Referenz `rel_path` (`atelier/…`) + Atelier-Root →
  absoluter Pfad → `fileUrl()` (`/api/files?path=…&token=…`). Map `asset_id → {url, kind}`
  einmal aus `assets` + Root gebaut (`buildAssetMedia`).

## Dateien (alle < 200 Zeilen)
- `media/videocut/useCutPlayback.ts` — Clock, Transport, aktive-Clip-Helper, Timecode.
- `media/videocut/playbackSync.ts` — `useMediaSync` (Drift/Play/Pause/Volume).
- `media/videocut/OutputMonitor.tsx` — visueller Monitor (Video/Bild).
- `media/videocut/PlaybackAudio.tsx` — versteckte Audio-Elemente je Spur.
- `media/videocut/api.ts` — `buildAssetMedia` + `ClipMedia` ergänzt.
- `media/videocut/TrackArea.tsx` — Playhead + Scrub.
- `media/MediaPostProduction.tsx` — Verdrahtung Transport/Monitore/Zeit.

## Akzeptanzkriterien
- [ ] Play spielt die Timeline ab; Output-Monitor zeigt Videos und Standbilder zeitrichtig.
- [ ] Musik-/Sprache-/Effekt-Spuren spielen parallel (grobe Sync).
- [ ] Playhead läuft mit und ist per Klick/Scrub im Ruler verschiebbar.
- [ ] Transport: Anfang/Play/Pause/Stopp/Ende funktionieren; Play stoppt am Ende.
- [ ] Zeitanzeige zeigt Position / Gesamtlänge.
- [ ] Keine Backend-Änderung, Build/Typecheck/ESLint grün.
