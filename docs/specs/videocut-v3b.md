# Videoschnitt V3b — Schnittpunkte & Output-Assemblierung

## Was
Der rote Cut-Cursor kann per Button **„Schnittpunkt hinzufügen"** an seiner
Position einen **Schnittpunkt** fixieren. Schnittpunkte sind eigene, wieder
verschieb- und löschbare Marker auf der Zeitachse. Bei **Play** assembliert der
**Output-Monitor** das Endprodukt entlang der Schnittpunkte: er schaltet an
jedem Schnittpunkt zwischen vid1 und vid2 um.

## Warum
Kern des A/B-Roll-Schnitts. Erst der Schnittpunkt entscheidet, wo der Output von
Vid 1 auf Vid 2 (und zurück) umschaltet — dadurch muss man vid1 nicht bis zum
Ende und vid2 nicht vom Anfang nehmen. Baut auf V3a (Justage) auf, bereitet
Übergangseffekte (V3c) vor.

## Umschalt-Logik (Toggle mit Fallback)
- Output startet auf **vid1**.
- Jeder Schnittpunkt links von Position `t` **toggelt** die aktive Spur
  (0 Schnittpunkte davor → vid1, 1 → vid2, 2 → vid1, …).
- Hat die aktive Spur an `t` **keinen Clip** (Lücke), fällt der Output auf die
  andere Spur zurück (statt Schwarzbild). Hat auch die keine → „kein Signal".

## Wie
### Backend (kleine, additive Änderung)
- **`CutPoint`**-Model: `{ id: str, time: float }` (`time` in Sekunden, 0..86400).
- **`Timeline.cut_points: list[CutPoint]`** (default `[]`, `max_length` begrenzt).
  Pydantic-Validierung wie gehabt; `cut_points`-IDs müssen eindeutig sein.
- **`media_workspace.timeline()`**-Default + **`save_timeline()`**-Whitelist um
  `cut_points` erweitern (sonst wird das Feld beim Speichern verworfen).

### Frontend
- **Types/api**: `MediaCutPoint` + `cut_points` in `MediaTimeline`.
- **`assembleOutput.activeVideoAt(timeline, t)`**: reine Funktion → aktive
  `ActiveClip` nach obiger Logik (oder null).
- **`useCutTimeline`**: `addCutPoint(time)`, `moveCutPoint(id, time)` (+preview),
  `removeCutPoint(id)` — alle persistieren.
- **`OutputMonitor`**: nutzt `activeVideoAt` statt der V2-Regel „vid2>vid1".
- **`CutPointMarker`** (neu): weiße vertikale Linie mit Griff, ziehbar
  (Snapping an Clip-Kanten/0), Löschen per X. Über allen Spuren.
- **`TrackArea`**: rendert Schnittpunkt-Marker; reicht Add/Move/Remove durch.
- **`MediaPostProduction`**: Button „Schnittpunkt hinzufügen" (fügt am
  `cursorTime` hinzu), Zähler.

## Akzeptanzkriterien
- [ ] Button setzt am roten Cursor einen Schnittpunkt; Marker erscheint, persistiert.
- [ ] Schnittpunkte sind verschiebbar (persistiert) und löschbar.
- [ ] Bei Play schaltet der Output an jedem Schnittpunkt zwischen vid1/vid2 um.
- [ ] Lücke in aktiver Spur → Fallback auf andere Spur.
- [ ] `cut_points` überleben Reload (Backend round-trip).
- [ ] Backend-Test grün, Build/Typecheck/ESLint grün.
