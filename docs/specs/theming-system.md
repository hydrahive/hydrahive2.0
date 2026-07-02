# Theme-System — installierbare Designs (WordPress-Prinzip)

Status: **ENTWURF — wartet auf Freigabe**
Autor: Agent · Datum: 2026-07-02 · Branch-Ziel: `feature/theme-system`

## Was

Ein Design-/Theme-System für HydraHive2, bei dem ein **Theme** nicht nur Farben
tauscht, sondern das **komplette Layout + die Optik** — und als **eigenständiges
Paket** installierbar ist, das jeder User selbst bauen kann (wie ein Plugin/Modul).

Kernpunkte (von Till bestätigt):
1. Mehrere Themes stehen zur Auswahl.
2. User können **eigene Themes bauen** wie Plugins/Module.
3. Das **jetzige Design** ist als Standard-Theme mit dabei.

## Warum

Der bisherige `LookSwitcher`/`ThemeSwitcher` ändert nur Farbe & Form (CSS-Variablen).
Das ist zu wenig — ein „Designwechsel" muss auch das **Layout** ändern können
(Menü oben ↔ Menü links ↔ Grid), so wie ein WordPress-Theme die ganze Seite umbaut.

## Bestehende Patterns (wiederverwenden statt neu erfinden)

- **Modul-System**: `hydrahive2-modules/<id>/manifest.json` + `frontend/` → via
  `gen-modules.mjs` in `src/modules/index.generated.ts` gebündelt. Hub-installierbar
  über `hub.json`.
- **Plugin-System**: `plugins/{manifest,loader,installer,registry,hub_client}.py`
  mit `plugin.yaml` (name/version/description/permissions), Installer + Registry.
- **Layout**: steckt komplett in EINER Datei `frontend/src/shared/Layout.tsx`
  (134 Zeilen, `<header>`-Menü oben + `<main><Outlet/>`). ← der Angelpunkt.
- **CSS-Variablen**: `--hh-*` (Farbe/Form) + neue Look-Variablen aus `feature/ui-kit`.

→ Ein Theme = **dasselbe Muster wie ein Modul**, nur dass es statt einer neuen Seite
ein **Layout + CSS-Variablen-Set** liefert.

## Architektur-Entscheidung: EIN global aktives Theme

Wie WordPress: **genau ein Theme ist aktiv** und gilt für die ganze Oberfläche.
(Begründung: „wie Plugins" + „jetziges Theme mit drin" = ein austauschbares aktives
Design. Pro-Bereich-Themes wären eine spätere additive Erweiterung, kein MVP.)

Offen für Till: global-für-alle (Admin schaltet) vs. pro-User-wählbar. MVP: **pro
User in localStorage** (wie jetzt schon Theme/Look), Admin kann Default setzen.

## Theme-Paket — Aufbau

```
themes/<id>/
  theme.json           # Manifest
  layout.tsx           # exportiert default: React-Komponente mit <Outlet/>
  theme.css            # optional: CSS-Variablen + eigene Regeln (scoped)
  preview.jpg          # optional: Vorschaubild für den Theme-Picker
```

`theme.json`:
```json
{
  "id": "aurora",
  "name": "Aurora",
  "version": "1.0.0",
  "author": "till",
  "description": "Sidebar-Layout, ruhige Flächen.",
  "layout": "sidebar",            // welches eingebaute Layout-Gerüst (oder "custom")
  "variables": {                   // überschreibt --hh-* CSS-Variablen
    "--hh-r": "0.6rem",
    "--hh-accent-from": "rgb(2 132 199)"
  },
  "min_core_version": "2.0.0"
}
```

## Layout-Gerüste (eingebaut, von Themes wählbar)

`Layout.tsx` wird zerlegt in austauschbare Gerüste, die alle `<Outlet/>` + die
bestehende Nav-Config (`NAV_ITEMS`, `visibleItems`) nutzen — die 382 Seiten bleiben
**unangetastet**, nur das Gerüst drumherum wechselt:

- `topnav` — Menü oben (= aktuelles Design, 1:1 aus heutiger Layout.tsx extrahiert)
- `sidebar` — Menü links, Content rechts
- `grid` — Startseite als Kachel-Grid, Sekundär-Nav

Ein „custom"-Theme kann später eine eigene `layout.tsx` mitliefern (volle Freiheit).

## Umsetzung in Etappen

**Etappe 1 — Fundament (dieser PR):**
- `Layout.tsx` → `layouts/TopnavLayout.tsx` extrahieren (verhaltensgleich, 1:1).
- `LayoutHost` liest aktives Theme → wählt Gerüst + injiziert CSS-Variablen.
- Theme-Registry (`shared/themes/`) mit **2 mitgelieferten** Themes:
  „Standard" (topnav, heutiges Design) + „Sidebar" (Beweis dass Layout wirklich wechselt).
- Theme-Picker im Profil (ersetzt/erweitert LookSwitcher) mit Vorschau.
- **Akzeptanz:** Theme umschalten ändert sichtbar das Layout (oben↔links),
  Standard sieht 1:1 aus wie heute, Build + tsc strict grün.

**Etappe 2 — User-Themes (Paket-Loader):**
- `theme.json`-Loader + Codegen (`gen-themes.mjs` analog gen-modules).
- Themes aus einem `themes/`-Ordner einlesen (Dropin), Validierung.
- **Akzeptanz:** Ein Theme-Ordner reinlegen → erscheint im Picker.

**Etappe 3 — Hub/Installer (WordPress-Gefühl):**
- Theme über den bestehenden Hub installierbar (wie Module), Backend-Route.
- Optional: „Theme-Editor" im UI (Variablen live einstellen → als Paket exportieren).
- **Akzeptanz:** Theme aus Hub installieren/entfernen ohne Redeploy.

## Constraints

- Additiv — Standard-Theme = pixelgleich zum heutigen Design (kein Regressions-Risiko).
- Keine neue Fremd-Lib; React-Stack bleibt.
- Custom-Theme-CSS wird **scoped** geladen (kein globales Durchbluten fremder Regeln).
- Security: user-gebautes Theme-CSS darf kein JS ausführen; `layout.tsx` aus Hub =
  gleiche Vertrauensstufe wie ein Modul (Review/Signatur — in Etappe 3 klären).
- Max ~200 Zeilen/Datei, eine Verantwortung/Datei.

## Nicht in diesem Feature

- Pro-Bereich unterschiedliche Themes gleichzeitig (spätere additive Option).
- Theme-Marktplatz/Remote-Registry (erst wenn Hub-Weg steht).
