# Plan: Einstellungs-Hub wird „Meine Einstellungen“ (Schritt 2 von „ein Zuhause pro Einstellung“)

Task 36bd2884. Till hat am 26.10.2026 freigegeben. Vorbedingung erfüllt: PR #633 hat die
Lücken im Admin-Cockpit geschlossen (KI-Medien-Dienste, Credential-Warnung, Föderation).

## Ziel

`/settings` zeigt nur noch, was **jeder Nutzer für sich** einstellt. Admin-Dinge haben ihr
einziges Zuhause im Admin-Cockpit (`/admin?section=…`). Alte Adressen leiten dorthin um.

Bleibt in „Meine Einstellungen“ (Backend prüft pro Nutzer, `require_auth` + username):
**Agenten, Projekte, Kommunikation (Discord/WhatsApp), Skills, Butler, Zugangsdaten**.

Raus aus dem Hub, Weiterleitung (Admin-Fenster gibt es schon, gleiche API-Funktionen,
geprüft in Schritt 1):

| Hub-Gruppe        | neues Zuhause                       |
|-------------------|-------------------------------------|
| `modules`         | `/admin?section=modules`            |
| `plugins`         | `/admin?section=plugins`            |
| `themes`          | `/admin?section=themes`             |
| `extensions`      | `/admin?section=extensions`         |
| `mcp`             | `/admin?section=mcp`                |
| `llm`             | `/admin?section=llm`                |
| `federation`      | `/admin?section=federation`         |
| `connections`     | `/admin?section=system`             |
| `system`          | `/admin?section=system`             |
| `settings_values` | `/admin?section=system-settings`    |
| `users`           | `/admin?section=users`              |
| `zahnfee`         | `/admin?section=zahnfee` (neu, s. u.) |

**Zahnfee:** Die Einstellungen gibt es heute NUR im Hub (`ZahnfeeConfig`, Backend
`require_admin`), die Zahnfee-Seite verlinkt mit „Einstellungen“ auf `/settings`. Tills
Vorgabe (Kommentar in `registry.ts`): Auswertung und Einstellung bleiben getrennt. Deshalb
neues Admin-Fenster `/admin?section=zahnfee` mit `ZahnfeeConfig`, Kachel im Admin-Cockpit;
der Link auf der Zahnfee-Seite zeigt dorthin.

**MCP:** Normale Nutzer sehen MCP-Server heute im Hub nur lesend (anlegen/ändern ist
`require_admin`). Lesend bleibt es für sie über Werkstatt/Agenten erreichbar. Die
Server-Verwaltung ist Admin-Sache, deshalb raus.

**Mail-Hinweis** (Kommunikation → Mail): verweist auf „globale Settings“, die für Nicht-Admins
gar nicht erreichbar sind. Neu: Hinweis „Mail richtet der Admin unter Admin → Globale
Settings → Mail ein“, Link nur für Admins auf `/admin?section=system-settings`.

## Dateien

- `frontend/src/features/settings/legacyRedirects.ts` (neu): Tabelle `ADMIN_GROUP_TARGET`
  und `legacyTarget(groupId)`, liefert das Ziel oder `null`
- `frontend/src/features/settings/legacyRedirects.test.ts` (neu)
- `frontend/src/features/settings/registry.ts`: nur noch die 6 Nutzer-Gruppen; alle
  Admin-Imports raus; `adminOnly` entfällt (keine Admin-Gruppe mehr)
- `frontend/src/features/settings/registry.test.ts` (neu): genau diese 6 IDs, keine
  ID aus `ADMIN_GROUP_TARGET`
- `frontend/src/features/settings/SettingsHubPage.tsx`: bei `legacyTarget(groupId)` →
  `<Navigate replace>`; Kopf-Kontext „Deine persönlichen Einstellungen“
- `frontend/src/features/settings/SettingsHubPage.test.tsx` (neu): Umleitung und Gruppenliste
- `frontend/src/features/settings/GroupList.tsx`: Titel „Meine Einstellungen“, Etikett „Persönlich“
- `frontend/src/features/settings/tabs/CommunicationTabs.tsx`: Mail-Hinweis (s. o.)
- `frontend/src/features/cockpit/admin/ZahnfeeOverlay.tsx` (neu): AdminOverlay mit `ZahnfeeConfig`
- `frontend/src/features/cockpit/admin/adminOverlayRegistry.ts` (+ Test): `"zahnfee"`,
  `"/zahnfee-config": "zahnfee"`; `AdminOverlays.tsx`; Kachel in `AdminCockpitPage.opsLinks`
- `frontend/src/features/zahnfee/ZahnfeePage.tsx`: Link `/settings` → `/admin?section=zahnfee`
- `frontend/src/features/startdesk/areas.ts`: `/settings` aus Bereich „verwaltung“
- `frontend/src/features/startdesk/useAreas.ts`: `SETTINGS_HUB` entfällt
- `frontend/src/features/startdesk/areaLogic.test.ts`: Fall `/settings/llm` → verwaltung
  entfällt; neu: `/settings` ist in keinem Bereich
- `frontend/src/features/cockpit/CockpitUserMenu.tsx`: Text „Meine Einstellungen“
- `frontend/src/shared/AppFooter.tsx`: Modul-Update-Knopf → `/admin?section=modules`
  (bisher `/settings/modules`, würde sonst nur umgeleitet)
- `frontend/src/shared/layouts/TopnavLayout.tsx`, `SidebarLayout.tsx`: Zahnrad-Tooltip
  über i18n `settings.gear_tooltip` → „Meine Einstellungen“ (de) / „My settings“ (en)
- `frontend/src/i18n/locales/{de,en}/system.json`: `gear_tooltip`
- `frontend/src/i18n/locales/{de,en}/nav.json`: `settings_hub` → „Meine Einstellungen“

## Implementierungsreihenfolge

### Task 1: Umleitungstabelle
- [ ] Test `legacyRedirects.test.ts`:
  - alle 12 Admin-Gruppen liefern das Ziel aus der Tabelle oben
  - `agents`, `projects`, `communication`, `skills`, `butler`, `credentials`, `undefined` → `null`
  - jedes Admin-Ziel beginnt mit `/admin?section=` und die Section ist eine gültige
    `isAdminOverlayId`
- [ ] RED → `legacyRedirects.ts` → GREEN
- [ ] Mutante: Ziel von `connections` ändern → rot

### Task 2: Hub nur noch Nutzer-Gruppen
- [ ] Test `registry.test.ts`: IDs genau
      `["agents","projects","communication","skills","butler","credentials"]`; keine
      überschneidet sich mit den Schlüsseln von `ADMIN_GROUP_TARGET`; keine ist `adminOnly`
- [ ] RED → `registry.ts` ausdünnen (Reihenfolge: Agenten, Projekte, Kommunikation,
      Zugangsdaten, Skills, Butler) → GREEN
- [ ] Mutante: `llm` wieder hinzufügen → rot

### Task 3: Umleitung in der Seite und neuer Kopf
- [ ] Test `SettingsHubPage.test.tsx` (`renderToStaticMarkup` + `MemoryRouter` mit
      `<Routes>`; Ziel-Routen rendern Marker; `CockpitShell`/`CockpitTopbar` und die
      lazy-Inhalte gemockt):
  - `/settings/modules` → Marker der Admin-Route, nicht der Hub
  - `/settings/zahnfee` → Marker der Admin-Route
  - `/settings/agents` → Hub mit „Meine Einstellungen“
  - unbekannte Gruppe `/settings/xyz` → Hub (erste Gruppe), keine Umleitung
- [ ] RED → `SettingsHubPage` und `GroupList` → GREEN
- [ ] Mutante: Umleitung entfernen → rot

### Task 4: Start-Bereiche und Benutzermenü
- [ ] Test `areaLogic.test.ts` anpassen: `AREAS` „verwaltung“ enthält kein `/settings`.
      Test `useAreas` gibt es nicht; `SETTINGS_HUB` fällt mit weg (Typprüfung)
- [ ] RED → `areas.ts`, `useAreas.ts` → GREEN
- [ ] Benutzermenü-Text, Footer-Link, Zahnrad-Tooltip, i18n. Footer-Test erweitern:
      Knopf führt zu `/admin?section=modules` (Mutante: alter Pfad → rot)

### Task 5: Zahnfee-Einstellungen als Admin-Fenster
- [ ] Test `adminOverlayRegistry.test.ts`: `isAdminOverlayId("zahnfee")`,
      `OVERLAY_BY_PATH["/zahnfee-config"] === "zahnfee"`
- [ ] Test `ZahnfeePage.test.tsx` (`zahnfeeApi` gemockt): Link „Einstellungen“ zeigt auf
      `/admin?section=zahnfee`, nicht auf `/settings`
- [ ] RED → `ZahnfeeOverlay`, Registry, `AdminOverlays`, Kachel, `ZahnfeePage` → GREEN
- [ ] Mutanten: Registry-Eintrag entfernen, Link zurück auf `/settings` → rot

### Task 6: Mail-Hinweis
- [ ] Test `CommunicationTabs.test.tsx`: Rolle `user` → Hinweistext, kein Link; Rolle
      `admin` → Link `/admin?section=system-settings`
- [ ] RED → `CommMail` → GREEN

### Task 7: Prüfen und PR
- [ ] `tsc -b`, eslint (geänderte Dateien), vitest komplett, `vite build`
- [ ] Suche: kein `"/settings/<admin-gruppe>"` mehr im Code außer in `legacyRedirects.ts`
- [ ] GUI-Reise mit Till, danach PR, grüne CI, Merge

## GUI-Reise (mit Till)

1. Benutzermenü oben rechts → „Meine Einstellungen“ → links genau 6 Gruppen; jede öffnen.
2. Alte Adressen eintippen: `/settings/modules`, `/settings/llm`, `/settings/users`,
   `/settings/system` → landet im passenden Admin-Fenster.
3. Startseite → Bereich „Verwaltung“: kein „Einstellungen“-Eintrag mehr.
4. `/zahnfee` → „Einstellungen“ → Admin-Fenster Zahnfee öffnet sich; Kachel „Zahnfee“ im Admin-Cockpit.
5. Footer: bei Modul-Updates führt der Hinweis ins Admin-Fenster Module.
6. Als Nicht-Admin (`hydratest` ist Admin, deshalb ein Testnutzer ohne Admin-Rechte,
   wird danach gelöscht): „Meine Einstellungen“ zeigt dieselben 6 Gruppen, `/settings/modules`
   → `/admin…` → AdminGuard sperrt.

## Akzeptanzkriterien

- [ ] Jede Einstellung hat genau ein Zuhause; nichts ist verloren (Tabelle oben vollständig)
- [ ] Alte Links und Lesezeichen funktionieren (Umleitung)
- [ ] Dateien ≤ 200 Zeilen, alle Prüfungen grün, neue Tests vorher rot
- [ ] GUI-Reise von Till abgenommen

## Nicht in diesem Plan

- Hub optisch umbauen (Spalten, Reiter). Er hat danach nur noch 6 Gruppen.
- Seiten-Kürzungen System, Module, User, Archiv, Dashboard → Schritt 3 ff.
- Alte Einzelrouten (`/llm`, `/modules`, `/themes` …) in `App.tsx` auf `/admin` umleiten.
  Sie sind heute schon eigene Seiten. Das gehört zur Kürzung der jeweiligen Seite.
