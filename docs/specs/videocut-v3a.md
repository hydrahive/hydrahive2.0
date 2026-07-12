# Videoschnitt V3a — Justage-Fundament (A/B-Roll)

## Was
Der Videoschnitt wird zum echten A/B-Roll-Pult. Die beiden **Input-Monitore**
werden an die Video-Spuren gekoppelt: Input 1 zeigt vid1, Input 2 zeigt vid2 —
jeweils das Frame an der Position eines neuen, ziehbaren **roten Cut-Cursors**.
Clips lassen sich frei **horizontal verschieben** (Überlappung ausdrücklich erlaubt).

## Warum
Voraussetzung für Schnittpunkte (V3b) und Übergänge (V3c). Der rote Cursor +
die gekoppelten Monitore sind das Justier-Werkzeug: Beim Ziehen sieht man
gleichzeitig, welches vid1- und welches vid2-Frame an dieser Stelle liegt, und
findet so den perfekten Schnittmoment — ohne vid1 bis zum Ende oder vid2 vom
Anfang nehmen zu müssen.

## Warum nicht Trim/Split zuerst
Clips kürzen/teilen bringt nichts, solange man sie nicht verschieben und keine
Schnittpunkte setzen kann. Deshalb rückt das alte V3 (Trim/Split) hinter V3a–c.

## Wie
- **Backend: keine Änderungen.** Verschieben ändert nur `clip.start` (bestehendes
  Feld). Kein Kollisions-/Overlap-Schutz — Überlappung ist gewollt.
- **`useDragX`**: kleiner Pointer-Drag-Primitiv (window-Listener), rechnet
  Pixel-Delta → Sekunden-Delta. Für Clip-Drag und Cut-Cursor-Drag genutzt.
- **`moveClip(trackId, clipId, newStart)`** in `useCutTimeline`: setzt `start`
  (>= 0), persistiert. Während des Drags wird lokal (ohne PUT) gerendert, erst
  beim Loslassen gespeichert.
- **Clip-Drag** in `TrackArea`: Pointer-Down auf Clip-Body → horizontal ziehen.
  **Snapping** (Schwelle 0,4 s) an Clip-Kanten (Start/Ende aller vid1/vid2-Clips),
  an 0 und an den Cut-Cursor. Entfernen-Button (X) bleibt klickbar.
- **Roter Cut-Cursor** in `TrackArea`: vertikaler roter Balken über den Spuren mit
  Griff oben, ziehbar. Position = `cursorTime` (Parent-State). Live-Update beim
  Ziehen, kein Persist (reiner Ansicht-Cursor).
- **`InputMonitor`** (neu): zeigt für eine Spur (vid1/vid2) das eingefrorene Frame
  am `cursorTime` — Video via `<video>` auf `currentTime = localTime + source_in`
  gesetzt und pausiert; Bild via `<img>`; sonst „kein Signal".
- **Output-Monitor**: bleibt vorerst Playback wie V2 (vid2>vid1). Echte
  Ergebnis-Assemblierung entlang der Schnittpunkte kommt in V3b.

## Dateien (alle < 200 Zeilen)
- `media/videocut/useDragX.ts` — Pointer-Drag-Primitiv (neu)
- `media/videocut/InputMonitor.tsx` — track-gekoppelter Frozen-Frame-Monitor (neu)
- `media/videocut/useCutTimeline.ts` — `moveClip` ergänzt
- `media/videocut/TrackArea.tsx` — Clip-Drag + roter Cut-Cursor ergänzt
- `media/MediaPostProduction.tsx` — `cursorTime`-State, Input-Monitore koppeln

## Akzeptanzkriterien
- [ ] Input 1 zeigt vid1-Frame, Input 2 zeigt vid2-Frame am Cut-Cursor.
- [ ] Roter Cut-Cursor ist ziehbar; beide Inputs aktualisieren live.
- [ ] Clips lassen sich horizontal verschieben, dürfen überlappen, Position persistiert.
- [ ] Snapping an Clip-Kanten / 0 / Cursor.
- [ ] Clip-Entfernen funktioniert weiterhin.
- [ ] Keine Backend-Änderung, Build/Typecheck/ESLint grün.
