# Plan: Farbstufen + Kopffarben (Boxen besser abgrenzen)

Task `3bdd47d2`. Till 30.10.2026: „Infoboxen zu wenig abgetrennt, farblich nach Wichtigkeit abheben.“
Muster: Branch `muster/farbstufen`, Seite `/farbmuster`. Till hat **„Variante · Kopffarben“** gewählt
und den Weg „zentral statt Datei für Datei“ freigegeben.

## Ziel

Nach diesem Plan:

1. Boxen, Fenster und Innenzeilen haben **drei klar getrennte Helligkeitsstufen**. Jede Stufe ist heller als die darunter.
   Die Stufen sind **an einer Stelle** benannt (CSS-Variablen + Tailwind-Farben). Kein Bauteil trägt mehr eigene Dunkelblau-Werte.
2. Jede Box mit Thema trägt die **Farbe ihres Hydra-Kopfs**: Streifen links (4 px), leicht getönte, abgesetzte Kopfzeile.
3. Boxen können einen **Zustand** haben (`warnung`, `fehler`, `ok`). Warnung und Fehler übermalen die Kopffarbe (gelb/rot),
   immer mit Symbol + Wort, nie nur Farbe.

## Messwerte (Helligkeitsabstand, 1,00 = kein Unterschied)

| Übergang | heute | neu |
|---|---|---|
| Hintergrund → Box | 1,08–1,16 | 1,22 |
| Box → Kopfzeile | 1,01 | 1,13 |
| Box → Innenzeile | 1,04 (innen dunkler) | 1,24 (innen heller) |
| Box → Rand | 1,40 | 1,62 |

## Die Stufen (neue Namen → Wert)

| Name (CSS `--hh-s-*` / Tailwind `s-*`) | Wert | Rolle |
|---|---|---|
| `grund` | `#080b11` | App-Hintergrund (bleibt) |
| `tief` | `#0e141f` | Eingabefelder, Konsolen, Fußzeilen – eingelassen |
| `box` | `#172030` | Box / Fensterfläche |
| `kopf` | `#1f2a3d` | Kopfzeile von Box und Fenster |
| `innen` | `#243047` | Zeile/Karte in einer Box, normale Knöpfe |
| `hebung` | `#2b3852` | Hover von Innenzeilen/Knöpfen |
| `rand` | `#34425c` | Standardrand und Trenner |
| `rand-hover` | `#46617f` | Hover-/Fokusrand (bleibt) |

Schrift (WCAG 4,5:1 auf **allen** Stufen, gemessen): Haupttext `#e8eef8` (≥ 10:1), Nebentext neu `#9aa7bc`
statt `#8d9ab0` (≥ 4,8:1; alt wäre auf `hebung` nur 4,1). `#718097` und `#7d8aa0` werden zu `#9aa7bc`,
sobald sie auf `innen`/`hebung` liegen. Das prüft der Kontrast-Test in Task 4.

## Zuordnung alt → neu (Skript-Ersatz)

Die 64 Flächentöne werden nach Helligkeit einer Stufe zugeordnet, nicht von Hand:

| alte Werte (Beispiele, Anzahl) | neu |
|---|---|
| `#080b11` (20), `#0a1019` | `grund` |
| `#0b111c` (34), `#0d1420` (98), `#0e1420`, `#0c121d`, `#0b131f`, `#0d141f`, `#0c131e` | `tief` |
| `#151c2b` (37), `#101724` (40), `#111827` (90), `#121a29`, `#111b29` (29) | `box` bzw. `innen` – siehe Regel |
| `#131b2a` (12) | `kopf` |
| `#172133` (67), `#132235`, `#1b2536` (9) | `innen` / Hover → `hebung` |
| `#2a364b` (397), `#253247`, `#263247`, `#28354a`, `#2b394f`, `#1f2a3b`, `#223048`, `#1c2637` | `rand` |
| Akzent-/Statusflächen (`#163248`, `#1b3d56`, `#1c2940`, `#30243a`, `#104E8B`, Farbtöne) | **bleiben** |

**Regel für `#111827`/`#101724`/`#111b29`:** Diese Werte stehen heute sowohl für Boxen als auch für Zeilen *in* Boxen.
Das Skript entscheidet nach dem Element: Liegt das Element in einer `CockpitPanel`/`AdminOverlay`-Box
(heutiger Normalfall: Listenzeilen, Kacheln), wird es `innen`; steht es als oberste Fläche (Seitenleiste, Fenster,
Menü), wird es `box`. Fälle, die das Skript nicht sicher zuordnen kann, schreibt es in eine Liste. Die gehe ich von Hand durch
und halte sie im PR fest.

## Dateien

- `frontend/src/index.css` – Stufen als CSS-Variablen (`--hh-s-*`), alte `--cockpit-*` zeigen darauf
- `frontend/tailwind.config.js` – Farben `s-grund … s-rand-hover` (→ `bg-s-box`, `border-s-rand`)
- `frontend/src/shared/brand/boxThemes.ts` – je Thema eine `farbe` (Hex), aus der Streifen/Tönung entstehen
- `frontend/src/shared/brand/boxLook.ts` (neu) – rechnet aus Thema + Zustand: Streifenfarbe, Kopf-Tönung, Rand, Schild
- `frontend/src/shared/brand/BoxStatus.tsx` (neu) – Schild „Warnung/Fehler/Läuft“ mit Symbol
- `frontend/src/features/cockpit/CockpitPanel.tsx`, `project/CollapsibleCockpitPanel.tsx`,
  `admin/AdminOverlay.tsx`, `CockpitButton.tsx` – nutzen Stufen + `boxLook`
- `frontend/scripts/farbstufen-migrieren.mjs` (neu, einmalig) – Ersetzung alt → neu, `--pruefen` listet Reste
- Tests: `boxLook.test.ts`, `CockpitPanel.test.tsx` (erweitert), `farbstufen.test.ts` (Wächter + Kontrast)
- Spec: `docs/specs/admin-cockpit-visual-system.md` – Palette und Regel „Kopffarbe/Zustand“ aktualisieren
- Muster-Branch `muster/farbstufen` wird danach gelöscht (die Musterseite kommt nicht nach `main`)

## Implementierungsreihenfolge

### Task 1: Stufen zentral benennen
- [ ] Test `farbstufen.test.ts`: Tailwind-Farben `s-*` und CSS-Variablen `--hh-s-*` existieren mit den Werten oben;
      Kontrast jeder Schriftfarbe auf jeder Stufe ≥ 4,5:1, Rand ≥ 1,5 zur Box (ROT)
- [ ] Werte in `index.css` + `tailwind.config.js` eintragen, `--cockpit-*` darauf umbiegen (GRÜN)
- [ ] Commit

### Task 2: Kopffarbe + Zustand als Logik (`boxLook`)
- [ ] Tests `boxLook.test.ts` (ROT):
  - Thema ohne Zustand → Streifen = Kopffarbe, schwache Kopf-Tönung, normaler Rand, kein Schild
  - `warnung`/`fehler` → Streifen gelb/rot, stärkere Tönung, farbiger Rand, Schild mit Wort – **auch wenn die Kopffarbe anders ist**
  - `ok` → Kopffarbe bleibt, Schild „Läuft“
  - ohne Thema und ohne Zustand → neutral, kein Streifen
- [ ] `boxThemes.ts` um `farbe` ergänzen, `boxLook.ts` + `BoxStatus.tsx` schreiben (GRÜN)
- [ ] Commit

### Task 3: Bausteine umbauen (sofort überall sichtbar)
- [ ] `CockpitPanel.test.tsx` erweitern (ROT): abgesetzte Kopfzeile (`bg-s-kopf` + `border-b`), Streifen in Kopffarbe,
      neue Eigenschaft `status` zeigt Schild; bestehende Tests (Kopfbild, `data-box-theme`) bleiben grün
- [ ] Gleiches für `CollapsibleCockpitPanel` und `AdminOverlay` (Fensterkopf getönt, Fensterfläche `box`, Fuß `tief`)
- [ ] `CockpitButton` Normal-Knopf auf `innen`/`hebung`
- [ ] Bausteine umsetzen (GRÜN), der alte Verlauf `wash` entfällt
- [ ] Commit

### Task 4: Feste Werte per Skript ersetzen
- [ ] Wächter-Test in `farbstufen.test.ts` (ROT): keine der alten Flächen-/Randwerte aus der Tabelle mehr in
      `src/**` (ohne `src/modules/*`, die gehören den Modul-Repos)
- [ ] `scripts/farbstufen-migrieren.mjs` schreiben: ersetzt `bg-[#…]`, `border-[#…]`, `hover:…`, `from-/to-[#…]`
      (auch mit `/Transparenz`) nach der Tabelle; Nebentext `text-[#8d9ab0]` → `text-[#9aa7bc]`; Ausgabe: Liste unklarer Fälle
- [ ] Skript laufen lassen, unklare Fälle von Hand zuordnen (GRÜN)
- [ ] Danach Skript wieder löschen (einmalig, kein Dauerwerkzeug), Commit

### Task 5: Zustand an den Stellen setzen, wo er Sinn hat
Nur Boxen, die heute schon einen Zustand anzeigen. Kein neuer Zustand wird erfunden:
- [ ] Update verfügbar (Fußzeile/Update-Fenster) → `warnung`
- [ ] Module-/Plugin-Fenster: Modul mit Fehler bzw. Update → `fehler`/`warnung`
- [ ] Jobs/geplante Aufgaben: letzter Lauf fehlgeschlagen → `fehler`
- [ ] Nodes/System: Dienst offline → `fehler`, alles läuft → `ok`
- [ ] Je Stelle ein Test (Zustand aus Daten → richtiges Schild), Commit je Stelle

### Task 6: Spec + Prüfung
- [ ] `admin-cockpit-visual-system.md`: Palette auf Stufen-Namen, neue Regel „Kopffarbe = Thema, Gelb/Rot = Zustand, immer mit Wort“
- [ ] Volle Prüfung: vitest, tsc, eslint, `npm run build`
- [ ] Screenshots 1440 px + 390 px: Admin-Cockpit, 3 Admin-Fenster, Projekt-Cockpit, Buddy, Tresor, Medien
- [ ] Browser-Reise mit Till auf Testserver 5174, dann PR

## Akzeptanzkriterien

- [ ] Gemessene Abstände wie in der Tabelle „neu“ (Kontrast-Test grün)
- [ ] Jede Box mit Thema zeigt Streifen + getönte Kopfzeile in Kopffarbe
- [ ] Warnung/Fehler sind gelb/rot **mit Symbol und Wort**, unabhängig von der Kopffarbe
- [ ] Keine alten Flächen-/Randwerte mehr im Kern (Wächter-Test)
- [ ] Alle Schrift ≥ 4,5:1 auf jeder Stufe
- [ ] Kein Seitenüberlauf bei 390 px; Till hat auf dem Testserver abgenommen

## Nicht in diesem Plan

- **Modul-Frontends** (`src/modules/*`, 24 Dateien mit alten Werten): Sie gehören den Modul-Repos. Weil die
  alten `--cockpit-*`-Variablen auf die neuen Stufen zeigen, profitieren Module, die die Variablen nutzen, sofort.
  Feste Werte in Modulen kommen als eigener Folge-Task je Modul-Repo
- Alte `.box`-Karten außerhalb der Cockpits (Legacy-Seiten): Die `.cockpit-route`-Regeln biegen sie schon um
- Hell-Modus, Farbschema-Umschalter
- Neue Zustände erfinden (z. B. „Priorität“ ohne Datenquelle)
