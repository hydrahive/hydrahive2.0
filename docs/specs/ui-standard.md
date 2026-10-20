# HydraHive-UI-Standard (Barrierefreiheit und Bedienbarkeit)

## Status

Entwurf vom 2026-10-20. Grundlage: Messung aller Seiten im echten Browser (Task e1727aff).
Gilt für jede neue oder geänderte Oberfläche im Frontend. Bestehender Code wird schrittweise per PR nachgezogen.

## Was

Sieben verbindliche Regeln für Oberflächen, jeweils mit messbarem Kriterium (WCAG 2.2 Stufe AA),
dazu ein Messverfahren als Abnahme. Die Prüfideen stammen aus
[plugin87/ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) (MIT, v2.10.0)
und wurden für echte HydraHive-Seiten neu geschrieben (Login, Overlays, dunkles Theme).

## Warum

Messung vom 2026-10-20 (32 Seiten, axe-core 4.10.2 plus eigene Prüfungen):

| Befund | Anzahl |
|---|---|
| axe-Verstöße gesamt / davon kritisch | 133 / 55 |
| Buttons ohne Namen (nur Symbol) | 38 auf 8 Seiten |
| Auswahllisten und Felder ohne Namen | 12 + 5 |
| Kontrast unter 4,5:1 (axe) | 74 auf 15 Seiten |
| Klickflächen unter 24×24 px | 312 |
| Klickbare `div`s ohne Tastaturzugang | 64 |
| Overlays, hinter denen der Tab-Fokus weiterläuft | alle gemessenen Admin-Overlays |
| Horizontaler Überlauf bei 320 px | 0 |

Ursachen im Code (main 713754c8):

- Es gibt keine globale `:focus-visible`-Regel. Sichtbar ist nur der Standardring des Browsers
  (`#101010`, 1 px) auf dunklem Grund.
- `text-zinc-500` (`#71717a`, 526 Stellen) erreicht auf dem Panel `#1c2334` nur 3,24:1.
- `text-zinc-600` (261 Stellen) erreicht dort nur 2,03:1.
- Von 50 Dateien mit Vollbild-Overlays haben 23 `role="dialog"`. Fokusführung hat keines.
- 15 Felder setzen `outline-none` ohne Ersatz.

## Regeln

### 1. Text-Kontrast mindestens 4,5:1, große Schrift mindestens 3:1

Gemessen wird gegen den echten Hintergrund: Panel `#1c2334`, Overlay `#0e1420`,
Hover-Flächen bis `#232b3e`.

- Schwacher Text (Zeitstempel, Hinweise): `text-zinc-500`. Die Farbe wird zentral
  auf `#94949e` angehoben: 5,22:1 auf dem Panel, 4,70:1 auf Hover-Flächen, 6,16:1 auf `zinc-950`.
  Sie bleibt dabei unterscheidbar von `zinc-400` (`#a1a1aa`).
- `text-zinc-600` und `#5b6675` nur für Dekoration, nie für Information.
- Kein Alpha auf Text (`text-zinc-500/70`). Stattdessen eine passende Volltonfarbe.

### 2. Sichtbarer Fokus

- Global gilt: `:focus-visible` zeigt einen Ring von 2 px mit 2 px Abstand in `--hh-focus`.
- `outline-none` ist nur zusammen mit einem eigenen `focus-visible:`-Ersatz erlaubt.

### 3. Jedes Bedienelement hat einen Namen

- Ein reiner Symbol-Button braucht `aria-label`. `title` allein reicht nicht.
- `select` und `input` brauchen ein `<label htmlFor>` oder ein `aria-label`.
- Die axe-Regeln `button-name`, `select-name` und `label` müssen 0 Treffer ergeben.

### 4. Klickflächen mindestens 24×24 px (WCAG 2.5.8)

- Ein Symbol-Button mit 14–16-px-Icon braucht mindestens `p-1.5`.
- Ausnahme sind Links im Fließtext.

### 5. Klickbares ist per Tastatur erreichbar

- `onClick` gehört an `<button>` oder `<a href>`.
- Wenn ein `div` aus Layoutgründen klickbar bleiben muss, braucht es
  `role="button"`, `tabIndex={0}` und Enter/Leertaste.

### 6. Overlays sind echte Dialoge

Für jedes Vollbild-Overlay (`fixed inset-0`) gilt:

- Es hat `role="dialog"`, `aria-modal="true"` und `aria-labelledby`.
- Beim Öffnen springt der Fokus in den Dialog. Tab bleibt im Dialog.
- Escape schließt den Dialog, sofern keine Eingaben verloren gehen.
- Beim Schließen kehrt der Fokus zum Auslöser zurück.
- Umgesetzt wird das einmal in einem gemeinsamen Hook. Die Rahmen (`AdminOverlay` usw.) nutzen ihn.

### 7. Kein horizontaler Überlauf bei 320 px

Das ist der heutige Stand und bleibt so.

## Abnahme

Vor jedem UI-PR wird gegen den Testserver gemessen, nie gegen Prod.
Werkzeug: axe-core plus eigene Prüfungen für Kontrast, Fokus per Bildvergleich, Klickflächen,
Tastatur, Overlay-Falle und Überlauf bei 320 px.
In die PR-Beschreibung gehören:

- Vorher/Nachher-Zahlen der betroffenen Seiten
- ein Vorher/Nachher-Screenshot der geänderten Stelle

## Umsetzung in Etappen

1. **UI-Grundlagen** (dieser PR):
   - globaler Fokusring
   - `zinc-500` zentral anheben, **nur als Textfarbe** (`theme.extend.textColor`):
     Flächen (`bg-zinc-500`, 23 Stellen) und Ränder (`border-zinc-500`, 11 Stellen) bleiben unverändert
   - Dialog-Hook mit Fokusfalle in `AdminOverlay`
   - `aria-label` an den Symbol-Buttons mit Fund
2. Restliche Overlays auf den Dialog-Hook umstellen.
3. Klickflächen und klickbare `div`s.
4. Restliche Kontrast-Funde: `text-zinc-600` je Stelle prüfen (Information auf `zinc-500`,
   Dekoration bleibt), Alpha-Text, feste Hex-Farben wie `#5b6675`.
   Ein globales Anheben von `zinc-600` würde es mit `zinc-500` verschmelzen und
   9 Hintergründe mitändern, deshalb erfolgt diese Arbeit Stelle für Stelle.

## Nicht-Ziele

- Kein neues Farbschema und kein neues Design. Es geht um Bedienbarkeit und Lesbarkeit.
- Das helle Theme (`.light`) ist nicht im Umfang: Es wird derzeit nirgends eingeschaltet.
