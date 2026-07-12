# Videoschnitt — Trim & Split (Feinschnitt)

## Was
Zwei Feinschnitt-Operationen an einzelnen Clips:
- **Split**: einen Clip an der Playhead-Position in zwei Clips teilen.
- **Trim**: die linke oder rechte Kante eines Clips ziehen, um ihn zu kürzen
  (bzw. wieder zu verlängern, im Rahmen der Quelldauer).

## Warum
Bisher konnte man Clips nur ganz auf eine Spur legen und verschieben. Für einen
echten Schnitt muss man Clips kürzen und teilen können — der letzte fehlende
Kernbaustein des Schnittpults.

## Datenmodell (vorhanden, keine Backend-Änderung)
`Clip{ start, duration, source_in, … }`:
- `start` = Position auf der Timeline
- `source_in` = Startzeit innerhalb der Quelldatei
- `duration` = abgespielte Länge

Damit sind Trim/Split reine Umrechnungen — **kein** Backend-Change nötig.

## Operationen (rein, in timelineOps.ts, getestet)
- **`splitClipAt(tl, trackId, clipId, t)`**: t ist eine absolute Timeline-Sekunde
  innerhalb des Clips. Ergebnis: Clip A `duration = t − start`; Clip B (neue ID)
  `start = t`, `source_in = source_in + (t − start)`, `duration = Rest`. Liegt t
  nicht echt im Clip-Inneren (mit Mindestabstand), passiert nichts.
- **`trimClipEdge(tl, trackId, clipId, edge, newValue)`**:
  - `edge = "start"`: neue linke Kante bei `newValue` (Timeline-Sek). Verschiebt
    `start` und `source_in` um denselben Delta, `duration` gegenläufig. Begrenzt
    so, dass `duration ≥ MIN` und `source_in ≥ 0` bleibt.
  - `edge = "end"`: neue rechte Kante bei `newValue`. Nur `duration = newValue −
    start`, begrenzt auf `≥ MIN`. (Obergrenze durch echte Quelldauer wäre ideal,
    ist aber nicht immer bekannt → weich, ohne harte Obergrenze.)
- `MIN_CLIP_DURATION = 0.1 s`.

## UI
- **`ClipBlock`**: schmale Trim-Handles an linker/rechter Kante (erscheinen beim
  Hover). Ziehen → `trimClip`-Preview, Loslassen → persistiert. Der bestehende
  Body-Drag (Verschieben) bleibt; Handles haben Vorrang (stopPropagation).
- **Split-Button** (Schere-artig) in der Transport-Leiste: teilt den Clip der
  ausgewählten/aktiven Video-Spur an der Playhead-Position. Da beide Video-Spuren
  aktiv sein können, splittet der Button in **allen** Video-Spuren, die an der
  Playhead-Position einen Clip haben.

## Akzeptanzkriterien
- [ ] Split am Playhead macht aus einem Clip zwei, korrekt mit source_in/duration.
- [ ] Trim linke/rechte Kante kürzt den Clip; Mindestdauer wird eingehalten.
- [ ] Verschieben (Body-Drag) funktioniert weiterhin.
- [ ] Reine Ops per Sanity-Check verifiziert; Build/Typecheck/ESLint grün.
- [ ] Keine Backend-Änderung.
