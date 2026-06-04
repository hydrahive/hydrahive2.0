# Scratchpad → Modul (+ Modul-Agent-Tool-Vertrag) — Design

**Datum:** 2026-06-04
**Status:** freigegeben (Till), bereit für Implementierungsplan
**Kontext:** Erster Core→Modul-Port aus der ROADMAP-Portierungsliste. Ziel: „Core abspecken".
Scratchpad ist der kleinste, am besten verstandene Kandidat — und weil es Agent-Tools
mitbringt, etabliert dieser Port die wiederverwendbare Fähigkeit *„Module erweitern den
Agenten"*, die fast jeder spätere Port (Patientenakte, Datamining, Voice) braucht.

---

## Ziel

Scratchpad **vollständig** aus dem Core in ein **Opt-in-Modul** (Hub-Repo
`hydrahive2-modules/scratchpad/`) auslagern: UI + API + Service + die beiden Agent-Tools
(`read_scratchpad`, `write_scratchpad`) + der System-Prompt-Hinweis. Nach dem Port ist im
Core kein Scratchpad-Code mehr; eine frische Installation läuft ohne Scratchpad, wer es
will installiert das Modul per Klick.

**Verhalten bleibt erhalten, wenn installiert:** über ein Manifest-Flag landen die Tools +
der Hinweis nach Install automatisch bei den Master-Agenten — genau wie heute.

**Daten bleiben:** Scratchpad speichert dateibasiert (`data_dir/scratchpad/<user>/{user,agent}.md`),
keine DB-Tabelle, keine Migration. Die `.md`-Dateien bleiben beim Port unangetastet; nach
(Re-)Install des Moduls sind vorhandene Notizen sofort wieder da.

---

## Leitentscheidungen (von Till bestätigt)

1. **Agent-Tools via Manifest-Flag:** Ein Modul deklariert seine Tools (+ optional Prompt-Hinweis);
   ein Manifest-Flag `default_agent_tools: true` entscheidet, ob sie automatisch zu den
   Master-Defaults gehören. Scratchpad setzt es → heutiges Verhalten 1:1. Andere Module
   können ihre Tools opt-in lassen (Flag weglassen → Tools verfügbar, aber nicht in Defaults).
2. **Opt-in-Modul:** Nach dem Port wird Scratchpad aus dem Core entfernt. Kein „Default-Modul"-
   Konzept (YAGNI). Auf den eigenen Servern (.23/.22) installiert Till das Modul einmal nach.
3. **System-Prompt-Hinweis wird generisch:** Der heutige Hardcode (`if "read_scratchpad" in
   allowed_tools`) wird zu einer Tool-Eigenschaft `Tool.prompt_hint`. Der System-Prompt hängt
   den Hinweis jedes erlaubten Tools an, das einen hat. Entfernt den Spezialfall aus dem Core.
4. **Ein Spec, drei Phasen:** Der Vertrag wird generisch geschrieben, aber zusammen mit
   Scratchpad als Konsument geliefert und bewiesen (ein Vertrag ohne Konsument ist nicht
   verifizierbar).

---

## Architektur

### Phase 1 — Modul-Agent-Tool-Vertrag (Core, generisch)

Vier kleine Erweiterungen, symmetrisch zum bestehenden Router-/Migrations-Muster des
Modulsystems:

| Datei | Änderung |
|---|---|
| `core/src/hydrahive/modules/context.py` | `ModuleContext` bekommt `self.tools: list[Tool] = []` und `register_tool(self, tool: Tool) -> None`. Import `from hydrahive.tools.base import Tool`. |
| `core/src/hydrahive/tools/base.py` | `Tool`-Dataclass bekommt optionales Feld `prompt_hint: str = ""`. |
| `core/src/hydrahive/tools/__init__.py` | Neue Funktion `register_module_tools(tools: list[Tool]) -> None`: merged die übergebenen Modul-Tools idempotent in `REGISTRY` (vorher gemergte Modul-Tools werden anhand eines getrackten Namens-Sets `_MODULE_TOOL_NAMES` entfernt, dann neu hinzugefügt). So bleibt `REGISTRY` die *einzige* Tool-Quelle — alle bestehenden Konsumenten (`get_tool`, `schemas_for`, `_defaults._filtered`) funktionieren unverändert. |
| `core/src/hydrahive/modules/manifest.py` | `ModuleManifest` bekommt Feld `default_agent_tools: bool = False` (geparst aus `manifest.json`). |

**System-Prompt generisch** (`core/src/hydrahive/runner/system_prompt.py`):
- Entfernt: `_SCRATCHPAD_HINT`-Konstante + `if "read_scratchpad" in allowed_tools: stable += _SCRATCHPAD_HINT`.
- Ersetzt durch: Schleife über `allowed_tools` → für jedes Tool aus `REGISTRY` mit nicht-leerem
  `prompt_hint` wird der Hinweis an `stable` angehängt (stabile, cache-freundliche Reihenfolge:
  in `allowed_tools`-Reihenfolge).

**Default-Tools modul-bewusst** (`core/src/hydrahive/agents/_defaults.py`):
- `read_scratchpad`/`write_scratchpad` werden aus `_BASE_TOOLS["master"]` entfernt.
- Neuer lazy Helfer `_module_default_tool_names() -> list[str]`: lazy-import `hydrahive.modules.REGISTRY`;
  sammelt `[t.name for m in REGISTRY.values() if m.loaded and m.ctx and m.manifest.default_agent_tools
  for t in m.ctx.tools]`.
- `_filtered()` hängt diese Namen an die `master`-Liste an (weiterhin gefiltert gegen
  `tools.REGISTRY`, damit nur tatsächlich registrierte Tools übrig bleiben). `DEFAULT_TOOLS`
  löst bereits lazy auf (`_LazyDefaultTools`), konsultiert die Modul-Registry also bei jedem Zugriff.

**Lifespan-Verdrahtung** (`core/src/hydrahive/api/lifespan.py`):
- Direkt nach `module_system.load_all()` und neben `mount_module_routers(app)`:
  `register_module_tools([t for m in module_system.REGISTRY.values() if m.loaded and m.ctx for t in m.ctx.tools])`.
- Reihenfolge-Hinweis: `agent_bootstrap.ensure_master`/`migrate_tools` laufen *vor* dem
  Modul-Load. Das ist unkritisch, weil (a) bestehende Master ihre gespeicherte Tool-Liste
  behalten und (b) `DEFAULT_TOOLS` lazy auflöst — neu angelegte Agenten nach dem Modul-Load
  sehen die Modul-Default-Tools. (Falls sich später zeigt, dass ein frischer Erst-Boot-Master
  Modul-Tools braucht: Modul-Load vor `ensure_master` ziehen. Für Scratchpad als Opt-in-Modul
  irrelevant — beim Erst-Boot ist es nicht installiert.)

**Agent-Tool-Validierung** (`core/src/hydrahive/agents/_validation.py`): muss Modul-Tool-Namen
akzeptieren, wenn das Modul geladen ist (sie stehen dann in `REGISTRY`), und nicht-registrierte
Namen (Modul deinstalliert) tolerieren — analog zum bestehenden `OPTIONAL_TOOLS`-Mechanismus,
der entfernte Tools in alten Agent-Configs nicht als Validierungsfehler wertet. Der Plan prüft
die genaue Stelle und ergänzt die Toleranz, falls nötig.

### Phase 2 — Scratchpad-Modul (Hub-Repo `hydrahive2-modules/scratchpad/`)

```
scratchpad/
├── manifest.json
├── backend/__init__.py
└── frontend/
    ├── index.tsx
    ├── ScratchpadPage.tsx
    └── api.ts
```

- **manifest.json:** `{"id":"scratchpad","name":"Scratchpad","version":"1.0.0","icon":"StickyNote",
  "nav_group":"working","permissions":[],"has_service":false,"default_agent_tools":true,
  "min_core_version":"2.0.0"}`
- **backend/__init__.py:** enthält
  - den **Service** (1:1 aus `core/.../scratchpad/service.py` umgezogen — zwei Zonen, atomic
    write, 256 KB-Limit, `get_combined`). Schreibt weiter nach `settings.data_dir/scratchpad/<user>/...`
    (Modul importiert `from hydrahive.settings import settings`).
  - den **API-Router** (aus `api/routes/scratchpad.py`, 1:1): `GET ""` (liefert
    `user_content` + `agent_content`), `PUT ""` (schreibt Mensch-Zone), `DELETE /agent`
    (leert Agent-Zone) — via `require_auth`/`coded`. Mountet unter `/api/modules/scratchpad`.
  - die **zwei Tools** `read_scratchpad` + `write_scratchpad` (aus `tools/read_scratchpad.py`/
    `write_scratchpad.py`), inkl. `prompt_hint` auf `read_scratchpad.TOOL` (der heutige
    `_SCRATCHPAD_HINT`-Text).
  - `register(ctx)`: `ctx.register_router(router)` + `ctx.register_tool(READ_TOOL)` +
    `ctx.register_tool(WRITE_TOOL)`. **Keine** Migration, **kein** Service-Skript.
- **frontend/index.tsx:** `routes` (`/scratchpad` → `ScratchpadPage`), `nav`
  (`labelKey:"scratchpad"`, `icon:"StickyNote"`, group `working`, `roles:[]`), `i18n`
  (`{de:{scratchpad:{title:"Scratchpad", ...}}, en:{scratchpad:{title:"Scratchpad", ...}}}`).
  `title` ist gemäß Nav-Label-Konvention der Menü-Eintrag.
- **frontend/ScratchpadPage.tsx + api.ts:** aus `frontend/src/features/scratchpad/` umgezogen;
  `api.ts` BASE wechselt `/api/scratchpad` → `/modules/scratchpad` (api-client prefixt `/api`).
- **hub.json:** Eintrag `{"id":"scratchpad","name":"Scratchpad","path":"scratchpad"}` ergänzen.

### Phase 3 — Core-Removal + Cleanup

Erst nach erfolgreich gebautem + verifiziertem Modul. Entfernt:
- Backend: `scratchpad/` (Service + `__init__`), `api/routes/scratchpad.py` + Registrier-Zeile
  in `api/main.py`, `tools/read_scratchpad.py` + `tools/write_scratchpad.py` + ihre Imports
  und `REGISTRY`-Einträge in `tools/__init__.py`, `_SCRATCHPAD_HINT` + Scratchpad-Namen aus
  `_BASE_TOOLS["master"]` in `agents/_defaults.py`.
- Frontend: `features/scratchpad/`, App-Route + Import in `App.tsx`, nav-config-Eintrag in
  `shared/nav-config.ts`, i18n (`locales/{de,en}/scratchpad.json`, deren Import/NS-Registrierung
  und `ns`-Array-Eintrag in `i18n/index.ts`, `items.scratchpad` in `locales/{de,en}/nav.json`).
- Tests: `test_scratchpad_api.py`, `test_scratchpad_prompt.py`, `test_scratchpad_service.py`,
  `test_scratchpad_tools.py` (ihr Verhalten wird vom Modul-Smoke + Phase-1-Tests abgedeckt).
- **Bleibt:** die Daten-Dateien unter `data_dir/scratchpad/`.

---

## Datenfluss (unverändert zur heutigen Logik, nur verlagert)

1. Mensch editiert die User-Zone im Browser → `PUT /api/modules/scratchpad` → `service.save_user`.
2. Agent ruft `write_scratchpad` → `service.save_agent` (eigene Zone, Mensch-Zone tabu).
3. Agent ruft `read_scratchpad` → `service.get_combined` (beide Zonen beschriftet).
4. System-Prompt hängt den `prompt_hint` von `read_scratchpad` an, sobald das Tool erlaubt ist.

---

## Fehlerbehandlung

- Zonen-Größe > 256 KB → `ScratchpadTooLarge` → API `400 scratchpad_too_large`, Tool `ToolResult.fail`.
- Lesefehler einer `.md` → leer (geloggt), kein Crash.
- Modul nicht installiert → Tools nicht in `REGISTRY` → Runner filtert sie aus alten Agent-Configs,
  Validierung toleriert (kein Fehler).
- Modul-Load-Fehler isoliert (bestehendes Loader-Verhalten) — bricht den Start nicht ab.

---

## Tests & Verifikation

**Phase 1 (Core-TDD, neue Tests):**
- `register_module_tools` legt Modul-Tool in `REGISTRY` ab; erneuter Aufruf ersetzt statt zu duplizieren.
- `Tool.prompt_hint` wird in den System-Prompt injiziert, wenn das Tool in `allowed_tools` ist; sonst nicht.
- Modul mit `default_agent_tools:true` → seine Tools erscheinen in den Master-Defaults; ohne Flag nicht.
- `_filtered()` lässt nicht-registrierte Modul-Tools weg.

**Phase 2/3 (lokaler E2E-Smoke über das echte Modulsystem, Wegwerf, wie bei Notizbuch):**
- Modul lädt (`load_all`), Router gemountet, Tools registriert.
- API: `PUT` schreibt Mensch-Zone, `GET` liefert beide Zonen, `DELETE /agent` leert Agent-Zone,
  `PUT` der Mensch-Zone lässt Agent-Zone unberührt.
- Tool-Pfad: `write_scratchpad` schreibt `agent.md`; `read_scratchpad` liefert kombinierten Text;
  Mensch-Zone bleibt für den Agenten unschreibbar.
- Datenkontinuität: eine vorab angelegte `user.md` ist nach Modul-Load über die API sichtbar.

**Nach Removal:**
- Volle Backend-Suite grün (beweist: nichts hing verdeckt an Scratchpad).
- Frontend build + lint grün.

**Tills Schritt (Browser-E2E auf .23):** Modul installieren, Notiz schreiben/speichern, Agent-Notiz
prüfen, Menü-Label „Scratchpad".

---

## Was bewusst NICHT in diesem Spec ist (YAGNI)

- Kein „Default-Modul"/Auto-Install-Konzept.
- Keine Datenmigration (dateibasiert, bleibt liegen).
- Keine Änderung an anderen Tools/Features; der `prompt_hint`-Mechanismus wird nur generisch
  eingeführt, nicht auf andere Tools angewendet.
- Kein Uninstall-Datenlöschen (Modul-Garantie: Daten bleiben).
