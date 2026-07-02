# Theme-Pakete

Ein Theme wechselt das **komplette Layout** der Oberfläche (Menü oben ↔ links ↔
eigenes Gerüst) und kann Farben/Formen über CSS-Variablen anpassen — ohne den
Core-Code anzufassen. Vorbild ist das Modul-System.

## Ein Theme anlegen

Lege einen Ordner `src/themes/<deine-id>/` an. Beim nächsten `npm run dev` /
`npm run build` wird er automatisch eingelesen und erscheint im Profil unter
**Design**. (Der Generator `scripts/gen-themes.mjs` scannt diesen Ordner.)

```
src/themes/<id>/
  theme.json      # Pflicht — Manifest
  theme.css       # optional — eigenes CSS (nur aktiv wenn Theme gewählt)
  layout.tsx      # optional — eigenes Layout-Gerüst (volle Freiheit)
  preview.jpg     # optional — Vorschaubild (jpg/png/webp)
```

## theme.json

```json
{
  "id": "aurora",
  "name": "Aurora",
  "version": "1.0.0",
  "author": "dein-name",
  "description": "Kurzbeschreibung.",
  "layout": "sidebar",
  "variables": {
    "--hh-accent": "rgb(45 212 191)",
    "--hh-r": "0.7rem"
  }
}
```

- **`layout`** — Name eines eingebauten Gerüsts: `"topnav"` (Menü oben) oder
  `"sidebar"` (Menü links). Wird ignoriert, wenn du ein eigenes `layout.tsx`
  mitlieferst.
- **`variables`** — überschreibt `--hh-*` CSS-Variablen (Akzentfarbe, Radius, …).
  Verfügbare Variablen siehe `src/index.css`.

## Eigenes Layout (`layout.tsx`)

Für volle Freiheit exportiert `layout.tsx` eine React-Komponente als `default`.
Sie bekommt `{ chrome }` (Nav-Daten, Update-State) und rendert `<Outlet/>` selbst.
Als Startpunkt `src/shared/layouts/SidebarLayout.tsx` kopieren.

## Beispiel

`aurora/` in diesem Ordner ist ein vollständiges, funktionierendes Beispiel
(Sidebar-Gerüst + eigene Farben + theme.css).
