# Spec: Modul-Verwaltung — eine Liste, Beschreibungen, kontextabhängige Buttons

## Was

Die Modul-Verwaltung (`/settings/modules`) wird umgebaut:

1. **Eine einzige Liste** aller Module (installiert + verfügbar gemischt), statt
   zwei getrennter Sektionen. Die separate „Verfügbare Module"-Sektion entfällt.
2. Jedes Modul zeigt eine **2-Satz-Beschreibung** (aus dem Manifest).
3. **Kontextabhängige Buttons**:
   - nicht installiert → **Installieren**
   - installiert → **Aktualisieren** (nur hervorgehoben, wenn Update vorliegt) +
     **Deinstallieren**. Der Installieren-Button verschwindet nach Installation.
4. Der **Hilfe-Button** der Seite wird auffälliger.

## Warum

Die Trennung „installiert oben / verfügbar unten" ist unübersichtlich; ein Modul
tauchte doppelt gedacht auf (verfügbar-Liste zeigt auch Installiertes). Eine
Liste mit klarem Status pro Karte ist verständlicher. Beschreibungen helfen neuen
Nutzern zu verstehen, was ein Modul tut, bevor sie installieren.

## Wie (grob)

### Backend

- **`ModuleManifest`** (manifest.py): neues optionales Feld
  `description: str = ""`. In `load()` aus `d.get("description", "")` lesen.
- **`installer.available_description(module_id) -> str`** (neu, analog
  `available_version`): liest `description` aus dem Hub-Cache-Manifest (ohne
  git-pull). Fehler → "".
- **`GET /api/admin/modules`**: Antwort umbauen auf **eine** gemergte Liste
  `modules`, jeder Eintrag:
  ```
  {
    id, name, description,
    installed: bool,
    loaded: bool, error: str|null,          # nur wenn installed
    version: str|null,                       # installierte Version
    available_version: str|null,
    update_available: bool
  }
  ```
  Quelle: Hub-Index (alle bekannten Module) ⋃ REGISTRY (installierte). `name`/
  `description` bevorzugt aus REGISTRY-Manifest (installiert), sonst aus
  Hub-Cache. Rückwärtskompatibel: `installed`/`available` weiterhin mitliefern
  ist NICHT nötig (Frontend wird mitgezogen) — aber `update-count` bleibt.
- **`update-count`** bleibt unverändert.

### Frontend

- **types.ts**: `ModuleEntry` (vereinheitlicht) ersetzt Installed/Available-Split.
- **api.ts**: `listModules()` liefert `{ modules: ModuleEntry[] }`.
- **ModuleCard**: EINE Karte, die per `mod.installed` die Buttons wählt:
  - nicht installiert: „Installieren" (violett).
  - installiert: „Aktualisieren" (amber wenn `update_available`, sonst dezent) +
    „Deinstallieren". Version-Badge + ggf. Update-Badge „v1.0 → v1.2".
  - Beschreibung (2 Sätze) immer sichtbar.
  - Nach erfolgreicher Aktion → `onRefresh()` (Liste neu laden → Buttons wechseln).
- **ModulesPage**: eine Grid-Liste, sortiert (installiert zuerst, dann
  alphabetisch). Kopf behält „Alle updaten" (nur veraltete). Kein Collapse mehr
  nötig, aber „N Updates"-Zähler bleibt sinnvoll.
- **Hilfe-Button auffälliger**: `HelpButton` bekommt eine `prominent`-Variante
  (Text „Hilfe" + kräftigere Farbe/Border statt nur graues Icon). Auf der
  Modul-Seite (und generell nutzbar).

### Modul-Manifeste (hydrahive2-modules)

Alle 15 Module bekommen `description` (2 Sätze, deutsch) im `manifest.json`.
**Version-Bump**: Da sich die Manifeste ändern, hebe ich die Patch-Version jedes
Moduls an (z.B. 1.0.0 → 1.0.1), damit die Update-Erkennung greift und der User
das Beschreibungs-Update auch als Update sieht. (Versionierung macht der Agent.)

## Akzeptanzkriterien

- [ ] Eine Liste; keine „Verfügbare Module"-Sektion mehr.
- [ ] Jede Karte zeigt eine 2-Satz-Beschreibung.
- [ ] Nicht installiert → nur „Installieren". Nach Klick + Neuladen → „Aktualisieren"
      + „Deinstallieren", kein „Installieren" mehr.
- [ ] Update-Badge/Hervorhebung nur bei echtem Versions-Update.
- [ ] Hilfe-Button ist deutlich sichtbarer (Text + Farbe).
- [ ] Backend liefert `description`; fehlt sie, leerer String (kein Crash).
- [ ] `tsc` grün, `eslint` clean, Backend pytest + ruff grün.

## Nicht in Scope

- Keine Mehrsprachigkeit der Beschreibungen (einsprachig im Manifest).
- Kein Auto-Update.
