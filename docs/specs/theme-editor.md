# Theme-Editor & Ordner-Themes

## Ziel
Themes funktionieren wie Plugins: jedes echte Theme ist ein **Ordner** mit
HTML-Vorlagen (`<hh-…/>`-Bausteine + Layout + Tailwind), die man mit einem
visuellen **WYSIWYG-Editor** (GrapesJS) bearbeiten kann.

## Entscheidungen (Till, 2026-07-02)
- **Standard** bleibt fest im Code (`shared/themes/registry.ts`), unantastbarer
  Fallback (`DEFAULT_THEME_ID = "standard"`). Kein Ordner, keine Templates —
  reines Layout-Gerüst (Menü oben). Wird NIE vom Editor angefasst.
- **Sidebar (Test)** wird als Theme-Eintrag entfernt (brauchen wir nicht mehr).
  ACHTUNG: nur der Picker-Eintrag `id:"sidebar"` in registry.ts — das
  **Layout-Gerüst** `SidebarLayout` (via layouts/builtins.ts) MUSS bleiben,
  weil Aurora `layout:"sidebar"` nutzt.
- **Alle echten Themes** = Ordner wie Aurora (`src/themes/<id>/`), damit alle
  editierbar sind.

## Zwei Mechanismen (Ist-Zustand, wichtig zu verstehen)
1. **Layout-Gerüst** (Standard, SidebarLayout): bestimmt nur Menü-Position +
   Farben; Seiteninhalt = normale React-Seiten. KEINE editierbaren Vorlagen.
2. **Template-Theme** (Aurora): eigene HTML-Vorlage je Seite mit Bausteinen.
   NUR diese Sorte ist mit HTML-Editor bearbeitbar.

## Etappen
### Etappe 1 — Aufräumen (klein, sicher)  ← JETZT
- Theme-Eintrag "sidebar" aus BUILTIN_THEMES entfernen.
- SidebarLayout-Gerüst + builtins.ts unangetastet lassen.
- Verifikation: Aurora lädt weiter (nutzt sidebar-Layout), Standard=Default.

### Etappe 2 — Persistenz für Ordner-Themes
- Editierbare Themes müssen als echte Dateien auf dem Server liegen (nicht nur
  im Frontend-Build). Prüfen: kann core/hydrahive/themes/ (Hub-System)
  Templates lesen/schreiben? API zum Speichern einzelner Template-HTMLs.
- Build-Themes (aurora) sind read-only Vorlagen → Workflow "kopieren, dann
  editieren" in ein user-Theme.

### Etappe 3 — WYSIWYG-Editor (GrapesJS)
- Deps: grapesjs (BSD-3, 26k★), @grapesjs/react (MIT, offiziell),
  grapesjs-tailwindcss-plugin (MIT).
- Proof zuerst: <hh-…/> als GrapesJS-Blöcke registrieren, Export = sauberes
  Template-HTML das 1:1 unsere <route>.html wird. Standalone verifizieren.
- Dann Editor-Seite (Admin): Palette der Bausteine links, Canvas mitte,
  Attribute rechts (z.B. height an hh-buddy). Speichern → Etappe-2-API.

## Akzeptanzkriterien
- Standard bleibt fester Fallback, nie editierbar.
- Sidebar-Test-Eintrag weg, Aurora läuft weiter.
- Editor bearbeitet nur Ordner/user-Themes, speichert HTML das der
  TemplateRenderer identisch rendert.
- Rein additiv: bestehende Themes/Design bleiben unberührt.
