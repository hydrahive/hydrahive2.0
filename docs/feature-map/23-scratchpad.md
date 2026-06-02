# Scratchpad

> Subsystem: **Globaler Mensch→Agent-Scratchpad** von HydraHive2.
> Ein persistenter Ort pro User, an dem der Mensch (Till) handgeschriebene Ideen/Notizen
> in Markdown ablegt und sein Buddy/Masteragent diese liest und in einer **eigenen,
> physisch getrennten Zone** ergänzt. Bewusste Übergabefläche für unstrukturierte Gedanken —
> ergänzt das automatische Datamining-Gedächtnis (Proaktiver Recall) um expliziten,
> handgeschriebenen Input.
>
> Kanonische Spec: `SPEC.md:819-849` (Abschnitt „Scratchpad — Mensch→Agent-Ideenfläche").
> Design-Dok laut Spec: `docs/superpowers/specs/2026-05-31-scratchpad-design.md`.
> Status laut MEMORY: FERTIG + browser-verifiziert auf main (2026-05-31). v1.1-Backlog: Mermaid-Rendering.

---

## WAS  (jede Fähigkeit / Feature / Endpoint / Tool / UI-Komponente einzeln)

### Kern-Idee / Architektur-Garantie
- **Zwei physisch getrennte Markdown-Dateien pro User** statt einer geteilten Datei:
  - `user.md` — schreibt **nur der Mensch** (via Web-Konsole / API-PUT).
  - `agent.md` — schreibt **nur der Agent** (via `write_scratchpad`-Tool).
  - Die Trennung in zwei Dateien macht es **technisch unmöglich**, dass der Agent Tills Text überschreibt. (`core/src/hydrahive/scratchpad/service.py:1-8`)
- **Global pro User**, nicht projekt- oder agentengebunden, persistent über Sessions hinweg. (`SPEC.md:829`)

### Backend-Service (`scratchpad/service.py`) — Funktionen
- **Konstante `MAX_ZONE_BYTES`** = 256 KB pro Zone (`256 * 1024`). (`core/src/hydrahive/scratchpad/service.py:19`)
- **Exception `ScratchpadTooLarge(ValueError)`** — wird geworfen wenn Zone-Inhalt `MAX_ZONE_BYTES` überschreitet. (`core/src/hydrahive/scratchpad/service.py:22-23`)
- **`_zone_path(user_id, zone) -> Path`** — Pfad-Bauer: `data_dir/scratchpad/<user_id>/<zone>.md`. (`core/src/hydrahive/scratchpad/service.py:26-27`)
- **`_read(path) -> str`** — liest Datei, gibt `""` zurück wenn nicht vorhanden oder bei `OSError` (mit Warn-Log). (`core/src/hydrahive/scratchpad/service.py:30-37`)
- **`_write_atomic(path, content)`** — Größen-Check, dann atomarer Write via temp-Datei + `os.replace`. (`core/src/hydrahive/scratchpad/service.py:40-46`)
- **`get_user(user_id) -> str`** — liest Mensch-Zone. (`core/src/hydrahive/scratchpad/service.py:49-50`)
- **`save_user(user_id, content)`** — schreibt Mensch-Zone (atomar, größenbeschränkt). (`core/src/hydrahive/scratchpad/service.py:53-54`)
- **`get_agent(user_id) -> str`** — liest Agent-Zone. (`core/src/hydrahive/scratchpad/service.py:57-58`)
- **`save_agent(user_id, content)`** — schreibt Agent-Zone (atomar, größenbeschränkt). (`core/src/hydrahive/scratchpad/service.py:61-62`)
- **`clear_agent(user_id)`** — löscht die Agent-Zonen-Datei (nur wenn vorhanden; `path.unlink()`). (`core/src/hydrahive/scratchpad/service.py:65-68`)
- **`get_combined(user_id) -> str`** — fügt beide Zonen klar beschriftet zu **einem** Markdown zusammen; genau das Format das der Agent via `read_scratchpad` sieht. Leere Zonen werden als `_(leer)_` dargestellt. (`core/src/hydrahive/scratchpad/service.py:71-75`)

### REST-API (`api/routes/scratchpad.py`)
Router-Prefix: `/api/scratchpad`, Tag `scratchpad`. (`core/src/hydrahive/api/routes/scratchpad.py:14`)
- **Pydantic-Body `ScratchpadBody`** — `content: str` (default `""`, `max_length=262144` = 256 KB). (`core/src/hydrahive/api/routes/scratchpad.py:17-18`)
- **`GET /api/scratchpad`** — `get_scratchpad`: gibt **beide** Zonen zurück als `{"user_content": ..., "agent_content": ...}`. Auth-pflichtig (`require_auth`). (`core/src/hydrahive/api/routes/scratchpad.py:21-24`)
- **`PUT /api/scratchpad`** — `put_scratchpad`: speichert **nur** die Mensch-Zone (`service.save_user`). Bei `ScratchpadTooLarge` → `coded(400, "scratchpad_too_large", message=...)`. Antwort `{"saved": True}`. (`core/src/hydrahive/api/routes/scratchpad.py:27-37`)
- **`DELETE /api/scratchpad/agent`** — `clear_agent_zone`: leert **nur** die Agent-Zone (`service.clear_agent`). Antwort `{"cleared": True}`. (`core/src/hydrahive/api/routes/scratchpad.py:40-44`)
- Es gibt **bewusst keinen** PUT/POST-Endpoint für die Agent-Zone über die API — der Mensch kann die Agent-Zone nur **leeren**, nicht beschreiben. Beschreiben passiert ausschließlich über das Tool.

### Agent-Tools (`tools/read_scratchpad.py`, `tools/write_scratchpad.py`)
- **`read_scratchpad`** (Tool) — liest beide Zonen kombiniert via `service.get_combined(ctx.user_id)`. Leeres Input-Schema (`{}`). Kategorie `scratchpad`. Beschreibung: „Liest das Scratchpad des Users: Tills handgeschriebene Ideen plus deine eigenen Agent-Notizen." (`core/src/hydrahive/tools/read_scratchpad.py:6-24`)
- **`write_scratchpad`** (Tool) — schreibt **NUR** in die Agent-Zone (`service.save_agent`), **ersetzt sie komplett**. Erfordert `content: string` (Markdown). Validiert dass `content` ein String ist (`ToolResult.fail` sonst). Bei `ScratchpadTooLarge` → `ToolResult.fail`. Kategorie `scratchpad`. Beschreibung warnt: „Tills eigener Bereich ist tabu" und „Lies vorher mit read_scratchpad, damit du deine bestehenden Notizen nicht verlierst." (`core/src/hydrahive/tools/write_scratchpad.py:7-42`)

### System-Prompt-„Hinweis"-Mechanik (`runner/system_prompt.py`)
- **Statischer Prompt-Hinweis `_SCRATCHPAD_HINT`** — wird an den **stable** (cache-fähigen) System-Prompt angehängt, **nur wenn** `read_scratchpad` in `allowed_tools` ist. Erklärt dem Agent Existenz und Schreibgrenze des Scratchpads. (`core/src/hydrahive/runner/system_prompt.py:41-42`, `98-102`)

### Tool-Registry & Agent-Defaults
- Beide Tools sind in der zentralen Registry importiert und registriert. (`core/src/hydrahive/tools/__init__.py:32`, `42`, `69-70`, `90`)
- Beide Tools sind im **`master`-Agent-Default-Toolset** enthalten — also bekommt der Buddy/Masteragent sie automatisch. (`core/src/hydrahive/agents/_defaults.py:13`)
- `project`- und `specialist`-Agent-Typen bekommen die Scratchpad-Tools **nicht** per Default. (`core/src/hydrahive/agents/_defaults.py:16-25`)

### Frontend-Route & Navigation
- **Menüpunkt** im Nav: Pfad `/scratchpad`, Icon `StickyNote` (lucide-react), Label-Key `scratchpad`, Gruppe `working`. (`frontend/src/shared/nav-config.ts:33`)
- **Route** in `App.tsx`: `<Route path="scratchpad" element={<ScratchpadPage />} />`. (`frontend/src/App.tsx:70`)
- Import der Page in `App.tsx`. (`frontend/src/App.tsx:32`)

### Frontend-API-Client (`features/scratchpad/api.ts`)
- **`ScratchpadData`** Interface: `{ user_content: string; agent_content: string }`. (`frontend/src/features/scratchpad/api.ts:3-6`)
- **`scratchpadApi.get()`** → `GET /scratchpad`. (`frontend/src/features/scratchpad/api.ts:9`)
- **`scratchpadApi.saveUser(content)`** → `PUT /scratchpad` mit `{ content }`. (`frontend/src/features/scratchpad/api.ts:10`)
- **`scratchpadApi.clearAgent()`** → `DELETE /scratchpad/agent`. (`frontend/src/features/scratchpad/api.ts:11`)
- (Hinweis: `api`-Basis hängt automatisch `/api` davor, daher Pfad `/scratchpad` statt `/api/scratchpad`. (`frontend/src/shared/api-client.ts:27`))

### Frontend-View (`features/scratchpad/ScratchpadPage.tsx`)
- **Mensch-Zone (`Meine Ideen`)**: 2-Spalten-Grid mit links editierbarem `<textarea>` (monospace) und rechts Live-Markdown-Vorschau. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:48-62`)
- **Auto-Save (Debounce 800 ms)**: bei jedem `onChange` Timer-Reset, dann `scratchpadApi.saveUser`. Status-Anzeige `gespeichert`/`speichert…`. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:23-30`, `45`)
- **Agent-Zone (`Agent-Notizen`)**: read-only Markdown-Render, mit Hinweis „(nur der Agent schreibt hier)". (`frontend/src/features/scratchpad/ScratchpadPage.tsx:64-78`)
- **Leeren-Button** für Agent-Zone mit `confirm()`-Dialog → `scratchpadApi.clearAgent()`. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:32-35`, `68-73`)
- **Loading-Skeleton** während des initialen GET. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:37-39`)
- **Markdown-Rendering** via wiederverwendete `Markdown`-Komponente aus dem Chat-Feature (GFM, Task-Checkboxen, Syntax-Highlighting). (`frontend/src/features/scratchpad/ScratchpadPage.tsx:4`, `59`, `76`)
- **Theming**: setzt CSS-Var `--c` auf `rgbFor("/profile")` → Akzentfarbe `violet`. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:56`, `58`, `75`; `frontend/src/shared/colors.ts:34`)

### i18n (Namespace `scratchpad`)
- Eigener i18n-Namespace `scratchpad`, registriert in der NS-Liste und mit de/en-Bundles. (`frontend/src/i18n/index.ts:32`, `65`, `80`, `91`, `108`)
- Keys: `title`, `saved`, `saving`, `my_ideas`, `placeholder`, `empty_preview`, `agent_notes`, `agent_notes_hint`, `agent_notes_empty`, `clear`, `clear_confirm`. (`frontend/src/i18n/locales/de/scratchpad.json:1-13`, `frontend/src/i18n/locales/en/scratchpad.json:1-13`)
- Nav-Label `scratchpad` in de/en. (`frontend/src/i18n/locales/de/nav.json:15`, `frontend/src/i18n/locales/en/nav.json:15`)

### Tests
- `core/tests/test_scratchpad_service.py` — Service-Unit-Tests (Zonen-Trennung, Isolation, Größenlimit).
- `core/tests/test_scratchpad_api.py` — API-Roundtrip, Auth-Pflicht, Zone-Trennung.
- `core/tests/test_scratchpad_tools.py` — Tool-Verhalten, Registry-Präsenz, Master-Default.
- `core/tests/test_scratchpad_prompt.py` — Prompt-Hinweis nur bei zugewiesenem `read_scratchpad`.

---

## WIE  (Ablauf / Datenfluss, Schlüsselfunktionen)

### Datenfluss „Mensch schreibt Idee" (Web → Disk)
1. User tippt im `<textarea>` der ScratchpadPage. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:51-57`)
2. `onChange(v)` setzt lokalen State, markiert `saved=false`, startet 800-ms-Debounce-Timer. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:23-30`)
3. Nach 800 ms ohne Eingabe: `scratchpadApi.saveUser(v)` → `PUT /api/scratchpad` mit `{ content: v }`. (`frontend/src/features/scratchpad/api.ts:10`)
4. `put_scratchpad` ermittelt `user` aus `require_auth` (= JWT-`sub` / API-Key-Username), ruft `service.save_user(user, content)`. (`core/src/hydrahive/api/routes/scratchpad.py:27-37`)
5. `save_user` → `_write_atomic(_zone_path(user_id, "user"), content)`: Größen-Check (`MAX_ZONE_BYTES`), `mkdir -p`, temp-Datei `*.md.tmp` schreiben, `os.replace` (atomar). (`core/src/hydrahive/scratchpad/service.py:40-46`, `53-54`)
6. Datei landet unter `<HH_DATA_DIR>/scratchpad/<user_id>/user.md`. (`core/src/hydrahive/scratchpad/service.py:26-27`)

### Datenfluss „Agent liest Scratchpad" (Tool → LLM)
1. Im Runner wird der `ToolContext` mit `user_id=session.user_id` gebaut. (`core/src/hydrahive/runner/runner.py:82-84`)
2. Agent ruft `read_scratchpad` (leeres Args-Objekt). Dispatcher prüft `tool_name in allowed_tools`, dann `REGISTRY[tool_name].execute(args, ctx)`. (`core/src/hydrahive/runner/dispatcher.py:57`, `85-88`)
3. `read_scratchpad._execute` → `service.get_combined(ctx.user_id)`. (`core/src/hydrahive/tools/read_scratchpad.py:14-15`)
4. `get_combined` liest beide Zonen, stript, ersetzt Leeres durch `_(leer)_`, baut Markdown mit Überschriften `## Tills Ideen` und `## Agent-Notizen (dein Bereich)`. (`core/src/hydrahive/scratchpad/service.py:71-75`)
5. Ergebnis als `ToolResult.ok(text)` zurück → Dispatcher → `to_tool_result_block` → in die Anthropic-Message-History. (`core/src/hydrahive/runner/dispatcher.py:110-153`)

### Datenfluss „Agent schreibt Notiz" (Tool → Disk)
1. Agent ruft `write_scratchpad` mit `{ content: "<Markdown>" }`.
2. `_execute` validiert `isinstance(content, str)` (sonst `ToolResult.fail`). (`core/src/hydrahive/tools/write_scratchpad.py:25-28`)
3. `service.save_agent(ctx.user_id, content)` → `_write_atomic(_zone_path(user_id, "agent"), content)`. **Ersetzt** die gesamte Agent-Zone (kein Append). (`core/src/hydrahive/tools/write_scratchpad.py:30`, `core/src/hydrahive/scratchpad/service.py:61-62`)
4. Bei Überlänge → `ScratchpadTooLarge` → `ToolResult.fail(str(e))`, der LLM bekommt das als `FEHLER: ...` zurück. (`core/src/hydrahive/tools/write_scratchpad.py:31-32`; `core/src/hydrahive/tools/base.py:36-37`)
5. Datei landet unter `<HH_DATA_DIR>/scratchpad/<user_id>/agent.md`.

### Hinweis-Mechanik (der „Hybrid-Anbindung"-Teil)
Die Anbindung an den Agent ist **zweistufig (Hybrid)**, exakt wie in `SPEC.md:833-834` gefordert:
1. **Statischer Prompt-Hinweis** (cache-stabil): In `compose()` wird `_SCRATCHPAD_HINT` an den stable-Block angehängt — **aber nur** wenn `read_scratchpad` in `allowed_tools` steht. (`core/src/hydrahive/runner/system_prompt.py:41-42`)
2. **Tools** `read_scratchpad` + `write_scratchpad` als aktive Werkzeuge.
Der Hinweis lebt im **stable_system**-Block (nicht volatile), damit er den Anthropic-Prompt-Cache nicht bricht — siehe Cache-Doku im Modulkopf. (`core/src/hydrahive/runner/system_prompt.py:5-10`, `98-102`)

### Auto-Save-Mechanik (Frontend)
- Ein einziger `useRef`-Timer (`saveTimer`) wird bei jedem Tastendruck zurückgesetzt → klassischer Debounce ohne Custom-Hook. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:14`, `25-30`)
- Initialer Load via `useEffect([])`: GET, State setzen, `loading=false` in `finally`. Fehler werden mit `.catch(() => {})` verschluckt. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:16-21`)

### Atomic-Write-Detail
- `tmp = path.with_suffix(".md.tmp")` → ergibt für `user.md` die temp-Datei `user.md.tmp` (Suffix-Ersetzung auf `.md`). `tmp.write_text(...)` dann `os.replace(tmp, path)`. (`core/src/hydrahive/scratchpad/service.py:44-46`)

---

## WO  (Datei:Zeile für ALLES)

### Backend — Service
- Modul-Docstring (Zonen-Erklärung, Speicherpfad): `core/src/hydrahive/scratchpad/service.py:1-8`
- Imports (`logging`, `os`, `Path`, `settings`): `core/src/hydrahive/scratchpad/service.py:9-15`
- `logger`: `core/src/hydrahive/scratchpad/service.py:17`
- `MAX_ZONE_BYTES = 256 * 1024`: `core/src/hydrahive/scratchpad/service.py:19`
- `class ScratchpadTooLarge(ValueError)`: `core/src/hydrahive/scratchpad/service.py:22-23`
- `_zone_path(user_id, zone)`: `core/src/hydrahive/scratchpad/service.py:26-27`
- `_read(path)`: `core/src/hydrahive/scratchpad/service.py:30-37`
- `_write_atomic(path, content)`: `core/src/hydrahive/scratchpad/service.py:40-46`
- `get_user`: `core/src/hydrahive/scratchpad/service.py:49-50`
- `save_user`: `core/src/hydrahive/scratchpad/service.py:53-54`
- `get_agent`: `core/src/hydrahive/scratchpad/service.py:57-58`
- `save_agent`: `core/src/hydrahive/scratchpad/service.py:61-62`
- `clear_agent`: `core/src/hydrahive/scratchpad/service.py:65-68`
- `get_combined` (Format-String mit Überschriften): `core/src/hydrahive/scratchpad/service.py:71-75`
- Paket-Docstring: `core/src/hydrahive/scratchpad/__init__.py:1`

### Backend — API
- Modul-Docstring: `core/src/hydrahive/api/routes/scratchpad.py:1`
- Imports (`require_auth`, `coded`, `service`, `ScratchpadTooLarge`): `core/src/hydrahive/api/routes/scratchpad.py:9-12`
- Router (`prefix="/api/scratchpad"`): `core/src/hydrahive/api/routes/scratchpad.py:14`
- `ScratchpadBody` (max_length=262144): `core/src/hydrahive/api/routes/scratchpad.py:17-18`
- `GET ""` → `get_scratchpad`: `core/src/hydrahive/api/routes/scratchpad.py:21-24`
- `PUT ""` → `put_scratchpad` (+ ScratchpadTooLarge→coded 400): `core/src/hydrahive/api/routes/scratchpad.py:27-37`
- `DELETE "/agent"` → `clear_agent_zone`: `core/src/hydrahive/api/routes/scratchpad.py:40-44`
- Router-Mount in App: `core/src/hydrahive/api/main.py:49` (import), `core/src/hydrahive/api/main.py:123` (`include_router`)
- `coded()`-Helper: `core/src/hydrahive/api/middleware/errors.py:21-31`
- `require_auth()` (liefert `(username, role)`): `core/src/hydrahive/api/middleware/auth.py:36-50`

### Backend — Tools
- `read_scratchpad` Beschreibung: `core/src/hydrahive/tools/read_scratchpad.py:6-9`
- `read_scratchpad` Schema (leer): `core/src/hydrahive/tools/read_scratchpad.py:11`
- `read_scratchpad._execute`: `core/src/hydrahive/tools/read_scratchpad.py:14-15`
- `read_scratchpad` `TOOL`-Objekt (category `scratchpad`): `core/src/hydrahive/tools/read_scratchpad.py:18-24`
- `write_scratchpad` Beschreibung: `core/src/hydrahive/tools/write_scratchpad.py:7-11`
- `write_scratchpad` Schema (`content` required): `core/src/hydrahive/tools/write_scratchpad.py:13-22`
- `write_scratchpad._execute` (String-Check + TooLarge-Fail): `core/src/hydrahive/tools/write_scratchpad.py:25-33`
- `write_scratchpad` `TOOL`-Objekt: `core/src/hydrahive/tools/write_scratchpad.py:36-42`
- `Tool` / `ToolContext` / `ToolResult` Definitionen: `core/src/hydrahive/tools/base.py:8-57`
- `ToolResult.ok` / `.fail` / `.to_llm`: `core/src/hydrahive/tools/base.py:27-44`
- Tool-Imports in Registry: `core/src/hydrahive/tools/__init__.py:32` (`read_scratchpad`), `42` (`write_scratchpad`)
- Tool-Registrierung in `_build_registry`: `core/src/hydrahive/tools/__init__.py:69-70`
- `REGISTRY` global: `core/src/hydrahive/tools/__init__.py:90`
- `schemas_for(names)` (baut Anthropic-Schema): `core/src/hydrahive/tools/__init__.py:109-121`

### Backend — Agent-Defaults & Prompt
- Scratchpad-Tools im `master`-Default: `core/src/hydrahive/agents/_defaults.py:13`
- `_filtered()` / `_LazyDefaultTools` / `DEFAULT_TOOLS`: `core/src/hydrahive/agents/_defaults.py:29-58`
- `_SCRATCHPAD_HINT` Konstante: `core/src/hydrahive/runner/system_prompt.py:98-102`
- Hinweis-Anhängung in `compose()`: `core/src/hydrahive/runner/system_prompt.py:41-42`
- `compose()`-Signatur: `core/src/hydrahive/runner/system_prompt.py:18-49`

### Backend — Runner-Anbindung (Kontext-Fluss)
- `ToolContext`-Bau mit `user_id=session.user_id`: `core/src/hydrahive/runner/runner.py:82-84`
- `local_tools`/`allowed_tools`-Berechnung: `core/src/hydrahive/runner/runner.py:98-103`
- `compose_system_prompts(...)`-Aufruf (mit `allowed_tools`): `core/src/hydrahive/runner/runner.py:153-164`
- Tool-Dispatch (`execute_tool`): `core/src/hydrahive/runner/dispatcher.py:32-107`
- `allowed_tools`-Gate: `core/src/hydrahive/runner/dispatcher.py:57-60`
- Lokaler Tool-Aufruf `tool.execute(args, ctx)`: `core/src/hydrahive/runner/dispatcher.py:85-91`
- Result→Block-Konvertierung: `core/src/hydrahive/runner/dispatcher.py:110-153`

### Backend — Settings / Speicherpfad
- `data_dir` (`HH_DATA_DIR`, Default `/var/lib/hydrahive2`): `core/src/hydrahive/settings/_paths.py:19-21`
- (Kein eigener `scratchpad_dir`-Helper — Pfad wird inline in `_zone_path` gebaut.)

### Frontend — Page / API / Nav / Routing
- `ScratchpadPage`-Komponente (gesamt): `frontend/src/features/scratchpad/ScratchpadPage.tsx:1-81`
- State + Refs: `frontend/src/features/scratchpad/ScratchpadPage.tsx:10-14`
- Initialer Load (`useEffect`): `frontend/src/features/scratchpad/ScratchpadPage.tsx:16-21`
- `onChange` (Debounce-Save): `frontend/src/features/scratchpad/ScratchpadPage.tsx:23-30`
- `clearAgent` (confirm + DELETE): `frontend/src/features/scratchpad/ScratchpadPage.tsx:32-35`
- Loading-Skeleton: `frontend/src/features/scratchpad/ScratchpadPage.tsx:37-39`
- Mensch-Zone (textarea + Vorschau): `frontend/src/features/scratchpad/ScratchpadPage.tsx:48-62`
- Agent-Zone (read-only + Leeren): `frontend/src/features/scratchpad/ScratchpadPage.tsx:64-78`
- `Markdown`-Import: `frontend/src/features/scratchpad/ScratchpadPage.tsx:4`
- `ScratchpadData`-Interface: `frontend/src/features/scratchpad/api.ts:3-6`
- `scratchpadApi.get/saveUser/clearAgent`: `frontend/src/features/scratchpad/api.ts:8-12`
- `api`-Client (`/api`-Prefix, Auth-Header, 401-Logout): `frontend/src/shared/api-client.ts:24-61`
- `coded`-Fehler-Mapping im Client (`errors:<code>`): `frontend/src/shared/api-client.ts:13-22`
- Nav-Eintrag `/scratchpad` (StickyNote, group working): `frontend/src/shared/nav-config.ts:33`
- Route in App: `frontend/src/App.tsx:70`; Page-Import: `frontend/src/App.tsx:32`
- `rgbFor("/profile") → violet`: `frontend/src/shared/colors.ts:34`, `55`
- `Markdown`-Komponente (GFM, remark, Syntax-Highlight): `frontend/src/features/chat/Markdown.tsx:27-90`

### Frontend — i18n
- NS-Imports (`deScratchpad`/`enScratchpad`): `frontend/src/i18n/index.ts:32`, `65`
- NS-Registrierung in Resources: `frontend/src/i18n/index.ts:80`, `91`
- NS-Liste (`ns: [..., "scratchpad", ...]`): `frontend/src/i18n/index.ts:108`
- de-Bundle: `frontend/src/i18n/locales/de/scratchpad.json:1-13`
- en-Bundle: `frontend/src/i18n/locales/en/scratchpad.json:1-13`
- Nav-Label de/en: `frontend/src/i18n/locales/de/nav.json:15`, `frontend/src/i18n/locales/en/nav.json:15`

### Tests
- Service-Tests: `core/tests/test_scratchpad_service.py:1-65`
  - Zonen-unabhängig: `:25-29`
  - „Agent kann Tills Text nicht überschreiben"-Garantie: `:32-36`
  - `clear_agent` nur Agent-Zone: `:39-44`
  - User-Isolation: `:47-51`
  - `get_combined` enthält beide: `:54-59`
  - Größenlimit: `:62-64`
- API-Tests: `core/tests/test_scratchpad_api.py:1-37`
  - Leeres GET: `:4-7`
  - PUT→GET-Roundtrip: `:10-15`
  - PUT berührt Agent-Zone nicht: `:18-22`
  - DELETE Agent-Zone: `:25-32`
  - Auth-Pflicht (401): `:35-36`
- Tool-Tests: `core/tests/test_scratchpad_tools.py:1-53`
  - `read` liefert beide Zonen: `:22-28`
  - `write` nur Agent-Zone: `:31-36`
  - `write` lehnt Nicht-String ab: `:39-41`
  - Registry-Präsenz: `:44-47`
  - Master-Default: `:50-53`
- Prompt-Tests: `core/tests/test_scratchpad_prompt.py:1-30`
  - Hinweis bei zugewiesenem Tool: `:22-25`
  - kein Hinweis ohne Tool: `:28-30`

### Spec / Referenz
- SPEC-Abschnitt: `SPEC.md:819-849`
- Tool-Tabelle in SPEC: `SPEC.md:176-177`
- Design-Dok (laut Spec): `docs/superpowers/specs/2026-05-31-scratchpad-design.md`

---

## WARUM  (nicht-offensichtliche Verdrahtung, Annahmen, Gotchas)

### Sicherheits-/Integritäts-Designentscheidungen
- **Zwei-Dateien-Modell statt Zonen in einer Datei**: Die physische Trennung in `user.md`/`agent.md` ist die *technische* Garantie, dass der Agent Tills Text nicht überschreiben kann — es gibt schlicht keinen Code-Pfad, der vom Agent aus `user.md` schreibt. Die API hat bewusst **keinen** Agent-Zonen-PUT, das Tool hat bewusst **keinen** Zugriff auf `save_user`. (`core/src/hydrahive/scratchpad/service.py:1-8`; Test `:32-36`)
- **`user_id` = authentifizierter Username**: Der `user_id` im Pfad kommt aus `require_auth` (JWT-`sub` bzw. API-Key-Username), nicht aus Request-Body. Damit ist die Zone pro User isoliert und nicht fälschbar. Im Tool-Pfad kommt `user_id` aus `ToolContext`, der im Runner aus `session.user_id` gesetzt wird — d.h. der Agent schreibt immer in die Zone **seines Owners/Session-Users**, nie in eine fremde. (`core/src/hydrahive/api/routes/scratchpad.py:23`, `core/src/hydrahive/runner/runner.py:82-84`)
- **Atomic Write** (`tmp` + `os.replace`) verhindert korrupte/halb-geschriebene Dateien bei Crash/Concurrency. `os.replace` ist auf POSIX atomar. (`core/src/hydrahive/scratchpad/service.py:40-46`)

### Cache-Stabilität des Prompt-Hinweises
- Der `_SCRATCHPAD_HINT` wird **absichtlich** an den **stable**-Block gehängt, nicht an den volatile-Block. Anthropic prüft den gesamten System-Block byteweise für den Prompt-Cache (siehe MEMORY „Anthropic-Cache-Semantik"). Ein an den stabilen Block gehängter, unveränderlicher Hinweis bricht den Cache nicht. (`core/src/hydrahive/runner/system_prompt.py:5-10`, `41-42`, `98-102`)
- Der Hinweis hängt an `"read_scratchpad" in allowed_tools` — d.h. ein Agent ohne dieses Tool bekommt **weder** den Hinweis **noch** das Werkzeug. Konsequenz: `write_scratchpad` allein (theoretisch) ohne `read_scratchpad` würde **keinen** Prompt-Hinweis erzeugen. In der Praxis vergeben die Master-Defaults aber immer beide zusammen. (`core/src/hydrahive/agents/_defaults.py:13`)

### `write_scratchpad` ist replace, nicht append
- `save_agent` ersetzt die **gesamte** Agent-Zone. Die Tool-Beschreibung warnt explizit, vorher mit `read_scratchpad` zu lesen, sonst gehen bestehende Notizen verloren. Es gibt keinen Append-/Merge-Mechanismus — bewusst KISS. (`core/src/hydrahive/tools/write_scratchpad.py:7-11`, `30`)

### Frontend-Theming-Trick
- Die Page nutzt `rgbFor("/profile")` (= `violet`) als Akzentfarbe und schreibt sie in die CSS-Var `--c` am `.box`-Element; das CSS macht den Rest (Border/Glow). Das ist HH2-weite Konvention. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:56`; `frontend/src/shared/colors.ts:47`)
- Markdown wird über die **Chat-Markdown-Komponente** gerendert — d.h. die Scratchpad-Vorschau erbt automatisch GFM-Task-Checkboxen, Syntax-Highlighting und sogar Hydra-Emote-Rendering (remarkHydraEmotes), obwohl letzteres für Scratchpad irrelevant ist. Wiederverwendung statt Duplikat. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:4`; `frontend/src/features/chat/Markdown.tsx:27-90`)

### Pfad-Annahmen
- Speicher liegt unter `settings.data_dir / "scratchpad" / user_id / "{user,agent}.md"`. `data_dir` defaultet auf `/var/lib/hydrahive2`, override via `HH_DATA_DIR`. **Es gibt keinen dedizierten `scratchpad_dir`-Settings-Helper** — der Pfad ist inline in `_zone_path` zusammengesetzt. Wer den Speicherort verschiebt, muss `_zone_path` anfassen. (`core/src/hydrahive/scratchpad/service.py:26-27`; `core/src/hydrahive/settings/_paths.py:19-21`)
- **Test-Gotcha** (siehe MEMORY „settings.data_dir Freeze"): `data_dir` ist eine `@cached_property`. In Tests wird sie per `monkeypatch.setattr(settings, "data_dir", tmp_path)` überschrieben. Wenn ein anderer Import `settings.data_dir` zur Collection-Zeit liest, friert der Wert ein und vergiftet die Session — hydrahive-Imports in Tests müssen lazy bleiben. (`core/tests/test_scratchpad_service.py:10-13`)

### Fehler-Schwalbe im Frontend
- Alle drei API-Aufrufe (`get`, `saveUser`, `clearAgent`) fangen Fehler mit `.catch(() => {})` ab und tun **nichts** damit. Es gibt keine Fehler-UI, keinen Toast, kein Retry. Bei einem fehlgeschlagenen Save bleibt der Status-Text dauerhaft auf „speichert…" hängen (weil `setSaved(true)` nur im `.then` liegt). (`frontend/src/features/scratchpad/ScratchpadPage.tsx:18`, `28`, `34`)

### Größenlimit-Konsistenz
- Drei Stellen müssen synchron bleiben: Service `MAX_ZONE_BYTES = 262144`, API-Body `max_length=262144`, Tool-`content` (kein eigenes Limit, fängt nur Service-Exception). Aktuell konsistent (alle 256 KB). Ein Über-API-Verstoß wird **doppelt** geblockt: zuerst Pydantic `max_length` (422), und falls das umgangen würde, der Service-Check (400). (`core/src/hydrahive/scratchpad/service.py:19`; `core/src/hydrahive/api/routes/scratchpad.py:18`)

---

## Datenmodell  (Tabellen / Schemas / Events / Config-Keys / Env-Vars)

### Persistenz (Dateisystem, KEINE DB-Tabelle)
- Speicher ist **rein dateibasiert** — keine SQLite-/Postgres-Tabelle für das Scratchpad.
- Pfad-Schema: `<HH_DATA_DIR>/scratchpad/<user_id>/user.md` und `<HH_DATA_DIR>/scratchpad/<user_id>/agent.md`. (`core/src/hydrahive/scratchpad/service.py:26-27`)
- Temp-Datei beim atomaren Write: `<...>/user.md.tmp` bzw. `agent.md.tmp`. (`core/src/hydrahive/scratchpad/service.py:44`)
- Inhaltsformat: rohes UTF-8-Markdown, keine Metadaten/Header.

### API-Schemas
- Request `ScratchpadBody`: `{ content: str (default "", max_length 262144) }`. (`core/src/hydrahive/api/routes/scratchpad.py:17-18`)
- Response `GET`: `{ "user_content": str, "agent_content": str }`. (`core/src/hydrahive/api/routes/scratchpad.py:24`)
- Response `PUT`: `{ "saved": true }`. (`core/src/hydrahive/api/routes/scratchpad.py:37`)
- Response `DELETE /agent`: `{ "cleared": true }`. (`core/src/hydrahive/api/routes/scratchpad.py:44`)
- Fehler-Code (PUT, Überlänge): `{ "detail": { "code": "scratchpad_too_large", "params": { "message": "..." } } }`, HTTP 400. (`core/src/hydrahive/api/routes/scratchpad.py:36`)

### Tool-Schemas (Anthropic-Format)
- `read_scratchpad`: input_schema `{ "type": "object", "properties": {}, "required": [] }`. (`core/src/hydrahive/tools/read_scratchpad.py:11`)
- `write_scratchpad`: input_schema `{ "type": "object", "properties": { "content": { "type": "string", ... } }, "required": ["content"] }`. (`core/src/hydrahive/tools/write_scratchpad.py:13-22`)
- `ToolResult.result_type` ist hier immer `"text"` (Default). (`core/src/hydrahive/tools/base.py:25`)

### Frontend-Typ
- `ScratchpadData = { user_content: string; agent_content: string }`. (`frontend/src/features/scratchpad/api.ts:3-6`)

### i18n-Keys (Namespace `scratchpad`)
- `title`, `saved`, `saving`, `my_ideas`, `placeholder`, `empty_preview`, `agent_notes`, `agent_notes_hint`, `agent_notes_empty`, `clear`, `clear_confirm`. (`frontend/src/i18n/locales/de/scratchpad.json:2-12`)
- Nav-Key: `nav:scratchpad`. (`frontend/src/i18n/locales/de/nav.json:15`)

### Konstanten / Config-Keys
- `MAX_ZONE_BYTES = 256 * 1024` (256 KB pro Zone). (`core/src/hydrahive/scratchpad/service.py:19`)
- API `max_length = 262144`. (`core/src/hydrahive/api/routes/scratchpad.py:18`)
- Auto-Save-Debounce: 800 ms (Magic-Number, inline). (`frontend/src/features/scratchpad/ScratchpadPage.tsx:29`)

### Env-Vars
- `HH_DATA_DIR` — Basis für den Scratchpad-Speicher (Default `/var/lib/hydrahive2`). (`core/src/hydrahive/settings/_paths.py:19-21`)
- Keine scratchpad-spezifische Env-Var.

### Events / Hooks / Trigger
- **Keine** Events, keine Watcher, kein Hook, kein Cron. Der Scratchpad ist rein pull-basiert (GET / Tool-Read) und push-basiert (PUT / Tool-Write). Kein Trigger feuert irgendetwas beim Schreiben.

### Routing
- Backend: `GET|PUT /api/scratchpad`, `DELETE /api/scratchpad/agent`. (`core/src/hydrahive/api/routes/scratchpad.py:21`, `27`, `40`)
- Frontend: SPA-Route `/scratchpad`. (`frontend/src/App.tsx:70`)

---

## Offene Enden  (TODOs, tote / halbfertige Teile, Drift)

### BUG / Drift: fehlender i18n-Fehler-Code `scratchpad_too_large`
- Die API wirft bei Überlänge `coded(400, "scratchpad_too_large", message=...)` (`core/src/hydrahive/api/routes/scratchpad.py:36`).
- Der Frontend-API-Client mappt Fehler-Codes über `i18n.t("errors:<code>", ...)` mit `defaultValue: code` (`frontend/src/shared/api-client.ts:16-18`).
- **Aber**: In `frontend/src/i18n/locales/{de,en}/errors.json` existiert **kein** Key `scratchpad_too_large` (nur `iso_too_large` ist vorhanden — `frontend/src/i18n/locales/en/errors.json:91`). → Bei Überlänge würde dem User der **rohe Code-String** „scratchpad_too_large" als Fehlermeldung angezeigt, nicht eine lokalisierte Nachricht. **Dazu kommt:** im Frontend wird der Fehler ohnehin nie sichtbar (siehe nächster Punkt). Niedrige Praxis-Relevanz (256 KB Limit + 800-ms-Save), aber echte Drift zwischen Backend-Code und i18n-Tabelle.

### Halbfertig: keine Fehler-UI im Frontend
- `get`/`saveUser`/`clearAgent` verschlucken alle Fehler mit `.catch(() => {})` (`frontend/src/features/scratchpad/ScratchpadPage.tsx:18`, `28`, `34`). Kein Toast, kein Inline-Fehler, kein Retry. Ein dauerhaft fehlschlagender Save zeigt dem User nie einen Fehler; der Status hängt auf „speichert…". Der oben genannte `scratchpad_too_large`-Code würde also faktisch nirgends angezeigt.

### v1.1-Backlog: Mermaid-Rendering (bewusst Nicht-Ziel in v1)
- Die SPEC nennt Mermaid-Code-Blöcke als unterstützten Inhalt (`SPEC.md:830`), aber **Browser-Rendering von Mermaid ist explizites Nicht-Ziel der v1** (`SPEC.md:838`: „v1: Code-Block; Rendering = Ausbaustufe v1.1"). MEMORY („Scratchpad-Idee") führt Mermaid-Rendering als v1.1-Backlog. Tatsächlich existiert **keine** Mermaid-Integration im Frontend (kein Treffer für `mermaid` in `frontend/src/`). Mermaid-Diagramme werden aktuell als reiner Code-Block dargestellt, nicht gerendert.

### Bewusste Nicht-Ziele (v1) — kein Bug, nur fehlend per Design
- Bild-/Foto-Upload / Whiteboard: nicht vorhanden (Nicht-Ziel, `SPEC.md:839`).
- Pro-Projekt- / Pro-Agent-Scratchpads: nicht vorhanden — der Scratchpad ist strikt global pro User (Nicht-Ziel, `SPEC.md:840`).
- Versionierung / History: nicht vorhanden; jeder Save überschreibt komplett, kein Verlauf (Nicht-Ziel, `SPEC.md:841`).

### Mögliche Verbesserungen / Beobachtungen (kein konkreter TODO im Code)
- **Magic-Number 800 ms** für den Debounce inline ohne Konstante. (`frontend/src/features/scratchpad/ScratchpadPage.tsx:29`)
- **Kein Concurrency-Schutz zwischen Mensch und Agent**: Schreibt der Agent in `agent.md` während der User die Page offen hat, sieht der User die neue Agent-Notiz erst nach Reload (kein Polling/SSE). Die Agent-Zone in der UI ist ein Snapshot vom letzten GET. Kein Live-Update.
- **`get_combined` strippt** die Zonen-Inhalte für die Leer-Erkennung, gibt aber den **ungestrippten** Originaltext aus (über `get_user`/`get_agent` neu geholt). D.h. führende/abschließende Whitespaces bleiben im an den LLM gelieferten Text erhalten — minimal, kein Problem. (`core/src/hydrahive/scratchpad/service.py:71-75`)
- **`write_scratchpad` hat kein eigenes Längen-Pre-Check** — es verlässt sich vollständig auf die Service-Exception. Konsistent, aber der Fehler kommt erst beim Schreibversuch.
- **Prompt-Hinweis-Kopplung an `read_scratchpad`**: Wäre einem Agent (entgegen den Defaults) nur `write_scratchpad` zugewiesen, bekäme er keinen Prompt-Hinweis. (`core/src/hydrahive/runner/system_prompt.py:41`)

### Test-Abdeckung — gut, aber Lücken
- Backend ist solide getestet (Service, API, Tools, Prompt — siehe WO/Tests).
- **Nicht getestet**: der API-`PUT`-Überlängen-Pfad (`ScratchpadTooLarge` → 400-`coded`) hat keinen expliziten API-Test (nur der Service-Layer-TooLarge ist getestet, `core/tests/test_scratchpad_service.py:62-64`).
- **Nicht getestet**: das Frontend (`ScratchpadPage.tsx`) hat keine Unit-/E2E-Tests im gefundenen Test-Set; verifiziert wurde es laut MEMORY manuell im Browser.
