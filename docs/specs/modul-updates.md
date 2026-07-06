# Spec: Modul-Update-Erkennung, Übersichtlichkeit & Footer-Indikatoren

## Was

Drei zusammenhängende Verbesserungen der Modul-Verwaltung (`/settings/modules`):

1. **Update-Erkennung pro Modul** — anzeigen, wenn für ein installiertes Modul
   eine neuere Version im Hub bereitsteht (Versionsvergleich, Option A).
2. **Übersichtlichkeit** — installierte Module in eine **einklappbare** Sektion;
   zusätzlich ein **„Alle updaten"**-Button, der nur Module mit verfügbarem
   Update nacheinander aktualisiert.
3. **Footer-Indikator** — ein kleiner Blob im Seitenfooter, der auf verfügbare
   **Modul-Updates** hinweist (analog zum bereits existierenden Core-„↑").

## Warum

Nutzer sehen aktuell nicht, ob ein Modul veraltet ist. Die installierten Module
blähen die Liste auf. Und der Footer zeigt nur die Core-Version bzw. das
Core-Update, aber nichts zu Modul-Updates.

## Wie (grob)

### Backend

- **`installer.available_version(module_id) -> str | None`** (neu, öffentlich):
  liest die `version` aus `manifest.json` im Hub-Cache (via bereits vorhandenem
  `_cache_path_for`). Fehler/kein Manifest → `None`.
- **`installer.is_update_available(installed, available) -> bool`** (neu):
  Semver-Vergleich mit `packaging.version.Version`; bei Parse-Fehler Fallback auf
  String-Ungleichheit. `available > installed` → `True`.
- **`GET /api/admin/modules`** erweitern: pro installiertem Modul zusätzlich
  `available_version: str | null` und `update_available: bool`. (Der Endpoint
  pullt bereits den Hub — die Cache-Manifeste sind danach aktuell.)
- **`GET /api/admin/modules/update-count`** (neu, admin): liefert
  `{ count: N }` = Anzahl installierter Module mit `update_available`. Liest den
  **vorhandenen Cache ohne git-pull** (billig, für Footer-Poll geeignet).

### Frontend

- **types.ts**: `InstalledModule` um `available_version?: string | null` und
  `update_available?: boolean` erweitern.
- **api.ts**: `getModuleUpdateCount(): Promise<{count:number}>`.
- **ModuleCard (InstalledModuleCard)**: bei `update_available` ein Badge
  „Update: v{version} → v{available_version}" + Update-Button hervorheben
  (amber). Ohne Update: Button dezent, Text „Aktuell".
- **ModulesPage**:
  - Installierte Sektion **einklappbar** (Toggle im Sektionskopf; Default:
    eingeklappt, wenn > 0 installiert). Kopf zeigt „Installiert (N)" +
    „· M Updates" wenn vorhanden.
  - **„Alle updaten"**-Button (nur sichtbar, wenn ≥1 Update): fährt die Module
    mit `update_available` **sequentiell** durch (ein Stream nach dem anderen),
    danach ein `onRefresh`.
- **AppFooter**: zweiter Blob (nur `isAdmin`) für Modul-Updates: bei `count>0`
  ein amber „⬢ N", Klick → `/settings/modules`. Nutzt eine neue
  `moduleUpdateCount`-Prop; Datenquelle in `useLayoutUpdate` (admin-gated
  Einmal-Load; kein Poll-Zwang).

## Akzeptanzkriterien

- [ ] Ein installiertes Modul mit niedrigerer Version als im Hub zeigt Badge +
      hervorgehobenen Update-Button.
- [ ] Ist die installierte Version gleich/höher, kein Update-Hinweis.
- [ ] Kaputtes/fehlendes Hub-Manifest → kein Absturz, `update_available=false`.
- [ ] Installierte Sektion ist einklappbar; Update-Zähler im Kopf korrekt.
- [ ] „Alle updaten" aktualisiert genau die veralteten Module, sequentiell.
- [ ] Footer zeigt für Admins bei Modul-Updates einen Blob → Klick öffnet
      Modul-Seite. Für Nicht-Admins unsichtbar.
- [ ] `npx tsc --noEmit` grün; Backend pytest + ruff grün.

## Nicht in Scope

- Kein automatisches Update ohne Nutzer-Klick.
- Kein Commit-Fallback (Option A pur — Module ohne Versions-Bump gelten als
  aktuell; das ist gewollt).
- Keine Änderung am Update-Mechanismus selbst (`installer.update`).
