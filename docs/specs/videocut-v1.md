# Videoschnitt V1 — Clip-Bibliothek + Clips auf Spur legen

## Was
Erster funktionaler Slice des Videoschnitts im Media-Cockpit (Menüpunkt „Videoschnitt").
Clip-Bibliothek aus vorhandenen Atelier-Beständen, Clips per Klick auf Spuren legen,
dateibasierte Persistenz. Kein Playback (V2), kein Trim/Split (V3).

## Warum
Stückweiser Aufbau des Schnittpults (Roadmap-Task d40a4c59). V1 liefert das Fundament:
Datenfluss Bibliothek → Asset-Referenz → Timeline-Clip → Persistenz.

## Wie
- **Backend: keine Änderungen.** Wiederverwendet wird die vorhandene Timeline-API
  (`GET/PUT /api/projects/{pid}/media-projects/{slug}/timeline`, media_workspace.py)
  und die Asset-Referenz-API (media_assets.py).
- **Media-Projekt „schnitt"**: beim ersten Öffnen automatisch angelegt (list → create falls fehlt).
- **Spur-Mapping** (UI → Timeline-Track-Kind): Video 1→video, Video 2→video,
  Musik→music, Effekt→audio, Sprache→voice. 5 Default-Tracks mit festen IDs
  (vid1/vid2/music/fx/voice) beim ersten Speichern.
- **Bibliothek** speist sich aus Atelier-APIs des aktiven Projekts:
  - Bilder: `atelier/projects/{pid}/gallery` (GalleryItem.rel)
  - Videos: `atelier/projects/{pid}/videos` (VideoJob completed, video_rel, duration)
  - Musik: `atelier/projects/{pid}/audio/library` (AudioLibraryItem.rel)
- **Hinzufügen**: Item-Klick → Ziel-Spur (Video→vid1/vid2 wählbar, Audio→music/fx/voice
  wählbar, Bild→vid1/vid2 als Standbild 5s) → Asset-Referenz anlegen falls für
  rel_path noch keine existiert (rel_path = `atelier/<rel>`, source_project_id = aktives
  Projekt) → Clip ans Spur-Ende (start = Summe vorhandener Clips) → PUT timeline.
- **Dauer**: Video aus VideoJob.duration; Audio clientseitig via Audio-Element-Metadata
  (Fallback 30s); Bild 5s fest (editierbar ab V7).
- **Darstellung**: Clips als farbige Blöcke (proportional, feste px/s-Skala) mit Label,
  Dauer, Entfernen (X). Ruler zeigt dynamische Sekunden-Marken.
- **Dateien** (alle <200 Zeilen): `media/videocut/api.ts` (ensure+laden),
  `media/videocut/useCutTimeline.ts` (State+Ops), `media/videocut/ClipLibrary.tsx`,
  `media/videocut/TrackArea.tsx`, `MediaPostProduction.tsx` (Verdrahtung, Monitore bleiben Dummy).

## Akzeptanzkriterien
- [ ] Öffnen des Videoschnitts legt bei Bedarf still das Media-Projekt „schnitt" an
- [ ] Bibliothek zeigt Bilder/Videos/Musik des aktiven Projekts mit Thumbnail/Icon
- [ ] Klick legt Clip auf die gewählte Spur, Block erscheint proportional
- [ ] Timeline überlebt Reload (PUT/GET über vorhandene API)
- [ ] Clip entfernen funktioniert und persistiert
- [ ] Keine Backend-Änderung, Build/Typecheck/ESLint grün
