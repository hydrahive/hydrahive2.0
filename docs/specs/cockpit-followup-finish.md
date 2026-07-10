# Plan: Cockpit-Folgearbeit Buddy + Header-Menüs

## Ziel
Buddy, Media, Vault und Admin wirken als zusammengehörige Cockpits. Media/Vault/Admin erhalten ein einheitliches Header-Menü. Buddy verliert die alte isolierte Chat-Optik und wird in die Cockpit-Shell integriert, ohne Chat-/Tool-Confirm-/Widget-Funktionalität zu verlieren.

## Dateien
- `frontend/src/features/cockpit/CockpitHeaderMenu.tsx` — wiederverwendbares Header-Menü für Cockpit-Seiten.
- `frontend/src/features/cockpit/CockpitShell.tsx` — nimmt optional `menu` entgegen.
- `frontend/src/features/cockpit/MediaCockpitPage.tsx` — Header-Menü + mehr echte Arbeitsbereiche.
- `frontend/src/features/cockpit/VaultCockpitPage.tsx` — Header-Menü + mehr echte Schutz-/Arbeitsbereiche.
- `frontend/src/features/cockpit/AdminCockpitPage.tsx` — Header-Menü + mehr echte Admin-Übersicht.
- `frontend/src/features/buddy/BuddyPage.tsx` — Cockpit-Shell, Header-Menü, modernere Rails.

## Implementierungsreihenfolge

### Task 1: Gemeinsames Header-Menü
- [ ] `CockpitHeaderMenu` mit aktiven Einträgen, `window.open(..., "_self")` und Mockup/Settings/Primary-Links.
- [ ] Shell rendert Menü unter dem Titel.
- [ ] Media/Vault/Admin verwenden das Menü.
- [ ] Build grün.
- [ ] Commit: `feat(cockpit): add shared header menu`

### Task 2: Buddy modernisieren
- [ ] Buddy in `CockpitShell` einbetten.
- [ ] Buddy erhält Header-Menü mit Chat/Settings/Help/Clear.
- [ ] Layout bleibt dreispaltig, aber nutzt Cockpit-Farben/Panels/edge-to-edge.
- [ ] ToolConfirm, ModelPicker, ProjectPicker, Commands, Widgets bleiben funktional.
- [ ] Build grün.
- [ ] Commit: `feat(buddy): align buddy page with cockpit shell`

### Task 3: Media/Vault/Admin inhaltlich abrunden
- [ ] Media: Arbeitsmodus-Header, Produktionsboard, Library/Tools Links.
- [ ] Vault: Sensibilitätszonen, dokumentierte Aktionen, aktive Links zu Akte/Crypto/Scratchpad/Credentials/Memory/Datamining.
- [ ] Admin: Operations-Board, Integrationen, Recovery/Security Links, keine automatischen gefährlichen Aktionen.
- [ ] Build grün.
- [ ] Commit: `feat(cockpit): finish secondary cockpit pages`

## Akzeptanzkriterien
- [ ] `/buddy`, `/media`, `/vault`, `/admin` haben ein sichtbares Header-Menü.
- [ ] Buddy ist nicht mehr die alte alleinstehende Chat-Kapsel, sondern im Cockpit-Look.
- [ ] Kein automatischer Medienjob, Vault-Export, Admin-Wartungsjob oder Secret-Read beim Laden.
- [ ] Frontend-Build grün.
- [ ] Staging-Smoke: `/buddy`, `/media`, `/vault`, `/admin` liefern 200.

## Nicht in diesem Plan
- Keine neuen Backend-Endpunkte.
- Keine echten Vault-Lock/Unlock-Mechaniken.
- Keine Live-Systemmetriken mit Polling.
- Kein automatisches Ausführen von Medien-/Admin-/Vault-Aktionen.
