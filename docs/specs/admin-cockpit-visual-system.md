# Admin-Cockpit Visual System

## Status

Genehmigt am 2026-07-15: Option C — verbindliche UI-Bausteine und vollständige Migration aller aus dem Admin-Cockpit erreichbaren Unteransichten.

## Was

Das Admin-Cockpit erhält ein konsistentes visuelles System. Alle Admin-Overlays, Karten, Formulare, Dialoge, Statusanzeigen und erreichbaren Detailansichten werden auf gemeinsame Cockpit-Bausteine und eine begrenzte Farbpalette umgestellt.

Die bestehende Funktionalität und die Backend-APIs bleiben unverändert. Diese Arbeit ist ein Frontend-Design- und Navigations-Refactoring.

## Warum

Die strukturelle Overlay-Migration hat alte Komponenten teilweise unverändert in neue Cockpit-Rahmen eingesetzt. Dadurch mischen sich aktuell:

- Legacy-`box`-Komponenten mit Cockpit-Panels,
- dynamische `rgbFor`-/`--c`-Akzente,
- violette, indigofarbene, pinke, türkise und gelbe Dekorationsfarben,
- alte Zinc-/Gradient-Dialoge,
- unterschiedliche Radien und Control-Stile,
- sowie Links aus Overlays zurück in Legacy-Seiten.

Das Ergebnis besitzt keine durchgehende visuelle Hierarchie. Die neue Spezifikation beseitigt die Ursache, statt einzelne Farben lokal zu ersetzen.

## Visuelle Regeln

### Palette: Farbstufen (seit 30.10.2026, Plan `docs/plans/farbstufen-kopffarben.md`)

Flächen und Ränder stehen **nur** in `frontend/src/index.css` als `--hh-s-*`. Tailwind verweist darauf
(`bg-s-box`, `border-s-rand`, `bg-s-innen/80`). Feste Dunkeltöne wie `bg-[#151c2b]` sind verboten,
der Wächter-Test `shared/brand/farbstufen.test.ts` schlägt sonst an. Jede Stufe ist heller als die darunter.

| Stufe | Wert | Verwendung |
|---|---|---|
| `s-grund` | `#080b11` | App-Hintergrund |
| `s-tief` | `#0e141f` | eingelassen: Eingaben, Konsolen, Fußzeilen, Seitenleisten in Fenstern |
| `s-box` | `#172030` | Box, Fenster, Menü, Seitenpanel |
| `s-kopf` | `#1f2a3d` | Kopfzeile von Box und Fenster, Kopfleisten |
| `s-innen` | `#243047` | Zeile/Karte in einer Box, normale Knöpfe |
| `s-hebung` | `#2b3852` | Hover von Innenzeilen und Knöpfen |
| `s-rand` | `#34425c` | Standardrand und Trenner |
| `s-rand-hover` | `#46617f` | Hover-/Fokusrand |

Gemessene Abstände: Grund→Box 1,22 · Box→Kopf 1,13 · Box→Innen 1,24 · Box→Rand 1,62.

| Schrift | Wert | Verwendung |
|---|---|---|
| Primärtext | `#e8eef8` | Überschriften und Werte |
| Sekundärtext | `#9aa7bc` | Beschreibungen, Labels, schwache Hinweise. ≥ 4,8:1 auf jeder Stufe |
| Cockpit-Akzent | `#69d7ff` / `#c8f2ff` | Primäraktionen, Fokus, aktive Tabs, Icons |

### Kopffarbe und Zustand

- Jede Box und jedes Fenster mit Thema (`theme`) trägt die **Farbe seines Hydra-Kopfs**: 4-px-Streifen links,
  leicht getönte Kopfzeile, Etikett in Kopffarbe (Professor amber, Macher orange, Denker türkis, Träumer lila,
  Buddy mint). Quelle: `shared/brand/boxThemes.ts` (`farbe`), Logik in `shared/brand/boxLook.ts`.
- **Zustand** (`status`) nur aus echten Daten:
  - `warnung` und `fehler` **übermalen** die Kopffarbe (gelb `#fbbf24` / rot `#fb7185`), mit farbigem Rand.
  - `ok` lässt die Kopffarbe und zeigt nur das Schild.
- Das Schild (`BoxStatusSchild`) zeigt immer **Symbol und Wort**, nie nur Farbe.

### Semantische Farben

- Grün/Emerald: ausschließlich Erfolg, online, gesund oder abgeschlossen.
- Gelb/Amber: ausschließlich Warnung, ausstehend oder laufend.
- Rot/Rose: ausschließlich Fehler, offline oder destruktive Aktion.
- Ausnahme: Kopffarben der Hydra (Streifen/Tönung). Professor (amber) und Buddy (mint) sind Themenfarben, keine
  Zustände. Ein Zustand erscheint immer zusätzlich als Schild mit Wort.
- Sonst dürfen semantische Farben keine rein dekorative Card-, Avatar-, Blob-, Tag- oder Button-Farbe sein.

### Verbotene Legacy-Muster im Admin-Erreichbarkeitsbaum

- `box`, `box-h`, `box-b`, `box-static`
- `rgbFor(...)` und visuelle `--c`-Variablen
- dekorative Gradients
- Domainfarben wie Violet, Indigo, Fuchsia, Cyan oder Yellow
- uneinheitliche Zinc-Flächen und `border-white/...` als lokales Parallel-Design
- dekorative unscharfe Blobs/Glows
- Navigation aus einem Admin-Overlay zurück auf eine Legacy-Seite, wenn ein Cockpit-Overlay existiert

Ausnahme: Diese Muster dürfen außerhalb des Admin-Erreichbarkeitsbaums vorübergehend bestehen bleiben. Gemeinsam verwendete Komponenten müssen entweder vollständig migriert oder durch eine Cockpit-Variante ersetzt werden, ohne andere Bereiche unbeabsichtigt zu verändern.

## Gemeinsame Bausteine

Unter `frontend/src/features/cockpit/admin/ui/` werden kleine, darstellungsorientierte Komponenten angelegt:

- `AdminPanel`: einheitliche Card-/Gruppenfläche mit optionalem Titel, Beschreibung, Status und Aktionen.
- `AdminStat`: neutrale Kennzahlkarte ohne Blob; Cockpit-Cyan für Icon/Fokus.
- `AdminStatus`: Badge oder Punkt für neutral/success/warning/danger.
- `AdminField`: einheitliches Label, Hilfe, Input-/Select-Fläche und Fehlerzustand.
- `AdminToggle`: Cockpit-Cyan für den normalen aktiven Zustand; semantische Farbe nur bei echter Statusaussage.
- `AdminDialog`: gestapelter Dialog im AdminOverlay-Stacking-Context, ohne Legacy-`box` und ohne Backdrop-Close während laufender Aktionen.
- `AdminAction`: Button/Link mit `default`, `primary` und `danger`; `primary` ist einfarbig Cockpit-Cyan statt Gradient.
- `AdminCodeBlock`: neutrale Mono-/Logfläche.
- `AdminEmptyState` und `AdminFeedback`: konsistente Leer-, Lade-, Erfolgs- und Fehlerzustände.

Bausteine bleiben klein und erlauben `className`/Slots, damit keine zweite starre UI-Bibliothek entsteht. Bestehende `CockpitButton`, `CockpitPanel` und `AdminOverlay` werden verwendet oder intern ergänzt, wenn sie dieselbe Rolle bereits erfüllen.

## Migrationsetappen

### Etappe 1 — Referenzbereich System

- Gemeinsame Admin-UI-Bausteine einführen.
- `CockpitButton`-Primary-Gradient durch einfarbigen Cockpit-Akzent ersetzen.
- System-Statistiken neutralisieren; keine acht dekorativen Farben und keine Blobs.
- Health-Checks behalten Grün/Rot, weil dies echte Zustände sind.
- Sämtliche im System-Overlay sichtbaren Karten (`AgentLink`, `Tailscale`, `Bridge`, `Samba`, `Backup`, `Migration` einschließlich ihrer Unterkomponenten und Dialoge) auf das neue System umstellen.
- `SystemSettingsOverlay` direkt als gestapeltes Overlay aus `SystemOverlay` öffnen.
- `VoiceInstallModal` als `AdminDialog` umstellen; laufende Installation bleibt nicht versehentlich schließbar.
- `RestartModal` und Migration-Unterdialoge im selben Erreichbarkeitsbaum ebenfalls prüfen und migrieren, wenn sie Legacy-Stile verwenden.

### Etappe 2 — Users

- Avatar-Gradient entfernen.
- User-Zeilen, Rollenstatus und Aktionsbuttons vereinheitlichen.
- Create/Edit/Password-Dialoge sowie API-Key-Ansicht migrieren.
- Native `confirm()`-Dialoge für destruktive Aktionen durch Cockpit-Bestätigung ersetzen, sofern dies ohne Funktionsänderung möglich ist.

### Etappe 3 — Containers

- Container-Cards und Summary-Karten neutralisieren.
- `rgbFor`-/`--c`-Farben entfernen.
- Detailansicht als gestapeltes Cockpit-Overlay statt Legacy-Route öffnen.
- Console, Logs und Aktionsdialoge auf AdminDialog/AdminCodeBlock umstellen.
- Grün/Gelb/Rot nur für tatsächlichen Containerzustand oder Fehler verwenden.

### Etappe 4 — Vollständiger Admin-Audit

- Alle übrigen Admin-Overlays und ihre erreichbaren Unteransichten statisch und visuell prüfen.
- Funde aus `box`, `rgbFor`, `--c`, Gradient, Zinc, Violet/Indigo/Fuchsia/Cyan/Yellow bereinigen.
- Doppelte Verknüpfungen und Legacy-Routen entfernen.
- LLM-Catalog und weitere bereits erfasste Follow-ups in den Overlay-Fluss integrieren.

## Navigation und Stacking

- Ein Admin-Unterbereich bleibt beim Öffnen im Cockpit; kein kompletter Seitenwechsel zu einer Legacy-Route.
- Verschachtelte Overlays werden innerhalb des bestehenden `AdminOverlay`-Roots gerendert.
- Hauptoverlay: `z-50`; gestapelte Dialoge/Details müssen sichtbar darüber liegen.
- Laufende, nicht abbrechbare Operationen dürfen weder per Backdrop noch per Escape unbeabsichtigt geschlossen werden.
- Schließen eines Kind-Overlays kehrt zum Eltern-Overlay zurück und verwirft nicht dessen geladenen Zustand.

## Barrierefreiheit

- Dialoge verwenden `role="dialog"`, `aria-modal="true"` und eine benannte Überschrift.
- Icon-only-Aktionen besitzen `aria-label`/`title`.
- Aktive Tabs und Toggles exponieren `aria-selected` bzw. `aria-pressed`.
- Farbe ist nie der einzige Informationsträger für Status.
- Fokusrahmen verwenden den Cockpit-Akzent und bleiben sichtbar.

## Akzeptanzkriterien

- [ ] Alle im Admin-Cockpit sichtbaren Flächen folgen derselben Palette, denselben Radien und derselben Typografie-Hierarchie.
- [ ] Im Erreichbarkeitsbaum des Admin-Cockpits existieren keine dekorativen `rgbFor`-/`--c`-Akzente, Blobs oder Gradients mehr.
- [ ] Grün, Gelb und Rot werden nur semantisch eingesetzt.
- [ ] System, System-Settings und Voice-Installation bilden den freigegebenen Referenzbereich.
- [ ] Users und Containers einschließlich Unteransichten folgen anschließend demselben Muster.
- [ ] Keine aus einem Admin-Overlay erreichbare Aktion fällt unnötig auf eine Legacy-Seite zurück.
- [ ] Alle API-Aufrufe und bestehenden Funktionen bleiben erhalten.
- [ ] TypeScript, ESLint im Änderungsscope, Frontend-Build und Cockpit-Offline-Check sind grün.
- [ ] Eingeloggter visueller Browser-Test deckt Hauptoverlay, Kind-Overlay, Dialog, Lade-, Leer-, Fehler- und Erfolgszustand ab.

## Nicht Teil dieser Arbeit

- Backend-API-Änderungen.
- Neue Admin-Funktionen oder neue Berechtigungsmodelle.
- Redesign von Seiten, die vom Admin-Cockpit nicht erreichbar sind.
- Neuordnung der fachlichen Inhalte oder Entfernung bestehender Funktionen.
