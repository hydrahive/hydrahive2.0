# Videoschnitt V6b — Weiche Übergänge im Export

## Was
Die Übergangseffekte (Crossfade / Wipe / Fade-to-black), die man schon in der
Preview sieht, werden jetzt auch in die exportierte MP4 gerendert. Bisher (V6a)
wurden sie als Hartschnitt exportiert.

## Warum
WYSIWYG: die heruntergeladene Datei soll dem entsprechen, was man im Output-
Monitor sieht. V6b schließt die letzte Lücke zwischen Preview und Export.

## Warum NICHT ffmpeg `xfade`
`xfade` erwartet zwei zeitlich **aufeinanderfolgende** Streams und verkürzt die
Gesamtdauer um die Überblendzeit. Unser Export nutzt aber ein **Overlay-
Compositing-Modell** (jeder Clip als Layer mit `enable=between(...)` auf schwarzem
Grund), das das Timing exakt wie die Preview hält. Übergänge werden deshalb im
Overlay-Modell über **Alpha-Rampen** umgesetzt — timing-treu, kein Längenversatz.
Empirisch verifiziert (Frame-Sampling: Crossfade mischt, Wipe wischt, Fade geht
über Schwarz).

## Wie
### Assembly (`media_timeline_assembly.py`)
- Neue reine Funktion `video_render_plan(timeline) -> list[ClipRenderOp]`.
  Baut auf `video_onair_segments` auf und ergänzt je Clip die im Übergangsfenster
  nötigen Info. Fenster eines Schnittpunkts: `[time − d/2, time + d/2]`
  (effect ∈ {crossfade, wipe, fade-black}, d>0). Pro Clip:
  - `segments`: on-air-Basisintervalle (wie V6a; Hartschnitt-Grenzen).
  - `enter`: optionaler Übergang, mit dem der Clip **erscheint** (er ist der
    „danach"-Clip eines Schnittpunkts) → `{effect, at, duration}`.
  - `leave`: optionaler Übergang, mit dem der Clip **verschwindet** (er ist der
    „davor"-Clip) → für crossfade/wipe implizit durch das enter des Nachfolgers,
    für **fade-black** braucht der davor-Clip ein eigenes Fade-out.
  Der einbezogene Zeitbereich wird an den Fenster-Rändern erweitert, damit sich
  die Clips im Übergang überlappen.

### Export (`media_export.py`)
Pro Video-Clip wird aus der Render-Op die Filterkette gebaut:
- **crossfade** (enter): Overlay-Fenster nach links um `d` erweitern,
  `format=yuva420p,fade=t=in:st=<winStart>:d=<d>:alpha=1`.
- **fade-black**: enter-Clip `fade=in` ab Fenstermitte (`d/2`); der davor-Clip
  bekommt zusätzlich `fade=out` in der ersten Fensterhälfte, sodass zwischen den
  beiden der schwarze Base-Layer durchscheint.
- **wipe** (enter): Overlay mit `geq`-Alpha-Maske, die eine von links wachsende
  Kante erzeugt: `a='if(lt(X,W*clip((T-<winStart>)/<d>,0,1)),255,0)'`.
- **cut / d=0**: unverändert wie V6a (harte `enable`-Grenze).
- Audio: an Schnittpunkten mit Übergang ein kurzer `acrossfade`-artiger
  Lautstärke-Übergang ist optional; V6b hält Audio wie V6a (Clip-Volumes,
  amix) — der Bild-Übergang ist das Sichtbare.

## Akzeptanzkriterien
- [ ] Crossfade wird im Export als Überblendung gerendert (Mischframe in der Mitte).
- [ ] Wipe wird als von links wachsende Kante gerendert.
- [ ] Fade-to-black geht sichtbar über Schwarz.
- [ ] Hartschnitt (cut/d=0) bleibt unverändert (V6a-Verhalten).
- [ ] Gesamtdauer bleibt exakt (kein `xfade`-Längenversatz).
- [ ] Backend-Tests grün inkl. Frame-Sampling je Effekt; ruff clean.
