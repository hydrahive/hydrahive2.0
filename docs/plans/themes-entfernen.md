# Plan: Layout-Theme-System entfernen

Task 3c82a8d5. Till 29.10.2026: „die themes brauchen wir nicht mehr, ein theme reicht“ – „ja lege los“.

## Ziel

Danach gibt es nur noch **ein** Design (Cockpit-Rahmen). Weg sind: Theme-Pakete (Aurora), Theme-Auswahl im Profil,
Admin-Kachel „Themes“, Theme-Editor (GrapesJS), Seitenvorlagen (ThemedPage), die ungenutzten Layouts
(Topnav/Sidebar) und im Backend Theme-Installer, Theme-Hub und die Admin-API `/api/themes`.

**Bleibt:** das **Farbschema** (`shared/theme.ts`, Profil „Farbschema“: Violet/Cool/Warm/Forest/Mono). Das ist kein
Layout-Theme, sondern die Akzentfarbe des einen Designs. Ebenso bleiben die Box-Themen (`shared/brand/boxThemes.ts`,
Hydra-Köpfe) – gleicher Wortstamm, andere Sache.

Befund vorher (Browser 29.10.): Mit Aurora gewählt zeigen 13 Seiten die alte Aurora-Vorlage statt der echten Seite
(buddy, dashboard, communication, teamchat, vms, butler, federation, streaming, datamining, memory, mcp, skills,
zahnfee). Nach dem Plan zeigen alle die echte Seite, auch mit altem `hh-active-theme` im Browser.

## Teil A – Frontend (PR 1)

### Task A1: Wächter-Test (rot)
- [ ] `src/features/themesRemoved.test.ts`:
  - die Ordner `src/themes`, `src/shared/themes`, `src/shared/layouts`, `src/features/themes`,
    `src/features/themeeditor`, `src/features/themetemplates` und `scripts/gen-themes.mjs` existieren nicht
  - `App.tsx` enthält weder `ThemedPage` noch die Routen `themes`, `theme-editor`, `template-proof`
  - `package.json` nennt weder `gen-themes` noch `grapesjs`
  - kein Quelltext (außer diesem Test) verweist auf `hh-active-theme`, `hh-theme-change`, `shared/themes`,
    `shared/layouts`, `themetemplates`, `themeeditor`
- [ ] Test rot

### Task A2: Seitenvorlagen raus
- [ ] `App.tsx`: 16× `<ThemedPage route=… fallback={<X/>} />` → `<X />`; Routen `template-proof`, `theme-editor`,
  `themes` und die Imports entfernen
- [ ] `features/themetemplates/`, `features/themeeditor/` löschen (inkl. `registry.test.ts`)

### Task A3: Theme-Auswahl und Admin-Kachel raus
- [ ] `profile/ThemePicker.tsx` löschen, aus `ProfilePage.tsx` austragen (ThemeSwitcher = Farbschema bleibt)
- [ ] `features/themes/` löschen
- [ ] Admin: Kachel „Themes“ in `AdminCockpitPage.tsx`, `ThemesOverlay.tsx`, Eintrag in `AdminOverlays.tsx`,
  `adminOverlayRegistry.ts` (Typ + Liste + Pfad), `ADMIN_OVERLAY_THEME.themes` in `boxThemes.ts`, `TILE_ART["/themes"]`
  + `public/kacheln/themes.webp`
- [ ] Tests nachziehen: `boxThemes.test.ts` (OVERLAY_IDS), `tileArt.test.ts` (Liste), `legacyRedirects.test.ts`
  (`themes`-Weiterleitung: prüfen, wohin sie zeigt; zeigt sie auf `/admin?section=themes` → Eintrag entfernen)

### Task A4: Layout-Gerüst und Theme-Registry raus
- [ ] `shared/Layout.tsx`: Theme-State, `hh-theme-change`-Listener, Theme-Variablen- und Theme-CSS-Effekte entfernen;
  Kommentar „liefert das Theme“ korrigieren
- [ ] `shared/themes/`, `shared/layouts/` (inkl. `layoutLogo.test.ts`), `src/themes/` löschen
- [ ] `scripts/gen-themes.mjs` löschen, `package.json`: Skript `gen:themes` und Aufrufe in `dev`/`prebuild` entfernen
- [ ] alter Browser-Eintrag: `main.tsx` entfernt einmalig `localStorage["hh-active-theme"]` (Aufräumen, schadet nicht)

### Task A5: Abhängigkeiten
- [ ] `grapesjs`, `@grapesjs/react` aus `package.json` + `package-lock.json` (per `npm uninstall`)
- [ ] prüfen, dass sonst niemand `grapesjs` importiert

### Task A6: Grün + Prüfung
- [ ] Wächter-Test grün; Mutantenprobe (z. B. `ThemedPage` zurück in App.tsx → rot)
- [ ] vitest komplett, `tsc -b`, eslint (geänderte Dateien), echter `vite build` (Bundle-Größe vorher/nachher notieren)
- [ ] Browser 1440 + 390 px: die 16 früheren ThemedPage-Routen zeigen die echte Seite – auch mit gesetztem
  `hh-active-theme=aurora`; Profil zeigt „Farbschema“, kein „Design/Layout“-Picker; Admin-Cockpit ohne Kachel „Themes“;
  `/themes`, `/theme-editor`, `/template-proof` → 404-Seite; keine JS-Fehler

## Teil B – Backend (PR 2, nach Merge von PR 1)

### Task B1: Wächter-Test (rot)
- [ ] `core/tests/test_themes_removed.py`: Paket `hydrahive.themes` nicht importierbar; App hat keine Route mit
  `/api/themes`; `Settings` hat kein `themes_frontend_dir`/`theme_hub_*` mehr
- [ ] Test rot

### Task B2: Entfernen
- [ ] `core/src/hydrahive/themes/`, `api/routes/themes.py`, Einbindung in `api/main.py`
- [ ] `settings/_paths.py`: `themes_frontend_dir`, `theme_hub_cache`, `theme_hub_git_url`, `theme_hub_extra_git_urls`
- [ ] Override-Schlüssel `theme_hub_extra_git_urls` (Einstellungs-UI/Settings-Felder) suchen und mit entfernen
- [ ] alte Tests `test_theme_editor.py`, `test_theme_hub.py`, `test_theme_installer.py` löschen
- [ ] Daten: `data_dir/.theme-cache/` bleibt liegen (harmlos, kein Löschen fremder Daten); im PR erwähnen

### Task B3: Grün + Prüfung
- [ ] Wächter-Test grün, volle Backend-Testreihe, ruff (geänderte Dateien)
- [ ] Linux-Installer: grep nach `theme` in `installer/` – nichts ändern, nur prüfen, dass er nichts davon erwartet

## Akzeptanzkriterien
- [ ] Nur noch ein Design; das Farbschema funktioniert weiter
- [ ] Mit altem `hh-active-theme=aurora` sehen alle Seiten normal aus
- [ ] Keine toten Verweise (Wächter-Tests), alle Prüfungen grün, CI grün
- [ ] Linux-Installer unverändert

## Nicht in diesem Plan
- GitHub-Repo `hydrahive/hydrahive2-themes` (Theme-Hub) – Tills Entscheidung (archivieren/löschen)
- Farbschema (`shared/theme.ts`) und Box-Themen (`boxThemes.ts`) bleiben
- Ordner `.theme-cache` auf Servern wird nicht gelöscht
