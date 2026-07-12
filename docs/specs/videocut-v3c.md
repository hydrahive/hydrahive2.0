# Videoschnitt V3c — Übergangseffekte je Schnittpunkt

## Was
Jeder Schnittpunkt bekommt einen **Übergangseffekt** mit **Dauer**. Statt eines
harten Cuts blendet der Output am Schnittpunkt von Vid 1 auf Vid 2 (bzw. zurück)
über — z.B. Crossfade oder Wipe. Ein **Inspector** erscheint bei ausgewähltem
Schnittpunkt und lässt Effekt + Dauer einstellen.

## Warum
Letzter Baustein des A/B-Roll-Schnitts (nach Justage V3a und Schnittpunkten V3b).
Weiche Übergänge sind der visuelle Standard jedes Schnitts.

## Effekt-Typen (V3c)
- `cut` — Hartschnitt (Default, Dauer ignoriert, = bisheriges V3b-Verhalten)
- `crossfade` — Überblendung (Opacity)
- `wipe` — horizontaler Wisch (clip-path Overlay von links)
- `fade-black` — kurz nach Schwarz und wieder auf (über Zwischenblende)

## Umschalt-/Render-Logik
- Ein Schnittpunkt bei `time` mit Dauer `d` erzeugt ein Übergangsfenster
  `[time − d/2, time + d/2]` (zentriert um den Schnittpunkt).
- **Außerhalb** jedes Fensters: genau eine aktive Spur (V3b-Toggle, mit Fallback).
- **Innerhalb** eines Fensters: `base` = Spur vor dem Schnittpunkt, `overlay` =
  Spur nach dem Schnittpunkt, `progress` 0→1. Der Output rendert beide Layer
  und mischt sie je nach Effekt (Opacity/clip-path). `cut`/`d=0` → harte Umschaltung.
- Fallback bei Lücken bleibt erhalten (base/overlay können auf die jeweils andere
  Video-Spur zeigen).

## Wie
### Backend (additiv)
- `CutPoint` um `effect: Literal["cut","crossfade","wipe","fade-black"] = "cut"`
  und `duration: float = 0 (0..30)` erweitern. Rückwärtskompatibel (Defaults).
- Test: effect+duration round-trip.

### Frontend
- **`timelineOps.ts`** (neu, rein): `withDefaultTracks`, `probeDuration`, alle
  Clip-/Cut-Transformationen (add/remove/move) als pure Funktionen → entschlackt
  `useCutTimeline` unter die 200-Zeilen-Grenze. Neu: `updateCutPoint(patch)`.
- **`assembleOutput.outputLayersAt(timeline, t)`** → `{ base, overlay?, progress, effect }`.
  `base`/`overlay` sind `ActiveClip | null`.
- **`OutputMonitor`**: rendert base-Layer immer, overlay-Layer nur im Fenster mit
  Effekt-Styling (`crossfade`→opacity, `wipe`→clip-path inset, `fade-black`→
  Schwarzblende in zwei Halbphasen).
- **`transitions.ts`** (neu): Effekt-Metadaten (Label/Icon) + Style-Berechnung
  `overlayStyle(effect, progress)`.
- **`CutPointMarker`**: auswählbar (Klick), zeigt Effekt-Kürzel; selektierter
  Marker hervorgehoben.
- **`CutPointInspector`** (neu): Panel bei ausgewähltem Schnittpunkt — Effekt-Wahl
  + Dauer-Slider + Löschen.
- **`MediaPostProduction`**: `selectedCutId`-State, Inspector einblenden.

## Akzeptanzkriterien
- [ ] Schnittpunkt anklicken wählt ihn aus; Inspector zeigt Effekt + Dauer.
- [ ] Effekt/Dauer ändern persistiert und wirkt im Output bei Play.
- [ ] Crossfade/Wipe/Fade-to-black sind im Output sichtbar; `cut` bleibt hart.
- [ ] Übergangsfenster zentriert um den Schnittpunkt, Fallback bei Lücken erhalten.
- [ ] Alte Schnittpunkte ohne effect/duration → Hartschnitt (rückwärtskompatibel).
- [ ] Backend-Test grün, Build/Typecheck/ESLint grün.
