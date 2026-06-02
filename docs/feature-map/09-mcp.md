# MCP

> Subsystem: **Model Context Protocol** Integration in HydraHive2.
> Zwei klar getrennte Hälften:
> 1. **MCP-Client-Seite** (Core) — HydraHive verbindet sich als *Client* zu externen MCP-Servern (Filesystem, Git, GitHub …) und exponiert deren Tools an die Agenten-Runner-Schleife.
> 2. **MCP-Server-Seite** (`mcp-servers/`) — eigenständige FastMCP-Prozesse, die *fremden* Clients (Claude Code, Home Assistant, andere MCP-Server) Zugriff auf HydraHive geben (`hh_*` Tools). Diese laufen NICHT im Core, sie sprechen über die REST-API gegen HydraHive zurück.
>
> Phasen-Status laut `core/src/hydrahive/mcp/__init__.py:1-6`: „Phase 1 (jetzt): stdio … Phase 2 (später): HTTP/SSE". In der Realität sind alle drei Transports (stdio/http/sse) implementiert — der Kommentar ist veraltet.

---

## WAS

### A. MCP-Client-Layer (Core, `core/src/hydrahive/mcp/`)

**Server-Registry (CRUD, persistiert in JSON):**
- `config.list_all()` — alle konfigurierten Server als `list[dict]` (`config.py:38`)
- `config.get(server_id)` — einzelnen Server lesen (`config.py:42`)
- `config.create(...)` — neuen Server anlegen, validiert, Dubletten-ID-Check, atomarer Schreibvorgang (`config.py:49`)
- `config.update(server_id, **changes)` — Felder ändern; `id` + `created_at` sind geschützt (werden aus changes entfernt), `updated_at` neu gesetzt (`config.py:90`)
- `config.delete(server_id)` — Server aus JSON entfernen; gibt `bool` ob etwas gelöscht wurde (`config.py:106`)
- `config._load_all()` — liest `mcp_servers.json`, gibt bei JSONDecodeError `{"servers": []}` zurück (defensiv) (`config.py:19`)
- `config._save_atomic(data)` — schreibt nach `*.json.tmp` und `replace()` (atomar, kein Half-Write) (`config.py:30`)

**Connection-Pool / Manager (`manager.py`):**
- `manager._clients` — Modul-globales `dict[str, McpClient]`, max. 1 warmer Client pro Server-ID (`manager.py:26`)
- `manager._lock` — `asyncio.Lock` schützt Pool-Mutationen (`manager.py:27`)
- `manager._build(server_cfg)` — Factory: baut `StdioMcpClient` / `HttpMcpClient` / `SseMcpClient` je nach `transport`; wirft `McpValidationError` bei unbekanntem Transport (`manager.py:30`)
- `manager.connect(server_id)` — explizit verbinden; idempotent (gibt bestehenden verbundenen Client zurück); `KeyError` wenn Server nicht in Registry (`manager.py:55`)
- `manager.get_or_connect(server_id)` — lazy: gibt warmen Client zurück, verbindet bei Bedarf nach, ohne aktive Health-Probe (`manager.py:70`)
- `manager.disconnect(server_id)` — Client aus Pool poppen + `close()`; gibt `bool` (`manager.py:83`)
- `manager.disconnect_all()` — alle Verbindungen schließen (`manager.py:92`) — **NIRGENDS aufgerufen** (siehe Offene Enden)
- `manager.status()` — Snapshot `[{"id", "connected"}, …]` für die Status-Annotation (`manager.py:99`)
- `manager.list_tools(server_id)` — Tools listen mit automatischem Reconnect-bei-Fehler (`manager.py:107`)
- `manager.call_tool(server_id, tool_name, arguments)` — Tool aufrufen mit automatischem Reconnect-bei-Fehler (`manager.py:117`)

**Tool-Bridge (`tool_bridge.py`) — Anbindung an den Runner:**
- `tool_bridge.PREFIX = "mcp__"` und `SEP = "__"` — Naming-Konvention (`tool_bridge.py:15-16`)
- `tool_bridge.make_tool_name(server_id, tool_name)` → `mcp__<server>__<tool>` (`tool_bridge.py:22`)
- `tool_bridge.parse_tool_name(qualified)` → `(server, tool)` oder `None` wenn kein MCP-Name (`tool_bridge.py:26`)
- `tool_bridge.schemas_for_servers(server_ids)` — liefert Anthropic-Format-Tool-Schemas für alle Tools der Server, parallel + 60s gecached (`tool_bridge.py:37`)
- `tool_bridge.call(qualified_name, arguments)` — Dispatch eines MCP-Tool-Calls; gibt `None` wenn Name nicht MCP-formatiert (= „nicht für uns") (`tool_bridge.py:83`)
- `tool_bridge._schema_cache` — `dict[str, tuple[float, list[dict]]]`, TTL `_SCHEMA_TTL = 60.0` (`tool_bridge.py:18-19`)

**Transport-Clients (`client/`):**
- `McpClient` — Protocol-Interface, Lifecycle `connect → list_tools → call_tool* → close` (`client/base.py:22`)
- `McpTool` — Dataclass `{name, description, schema}` (`client/base.py:8`)
- `McpToolResult` — Dataclass `{success, content: list[dict], error}` (`client/base.py:15`)
- `render_tool_content(blocks)` — vereinheitlicht Tool-Antwort-Blöcke zu einem String (text-Attribut, dict-`type:text`, Fallback `str()`) (`client/base.py:35`)
- `StdioMcpClient` — Subprocess über stdin/stdout, ein Subprozess pro Server, lebt bis `close()` (`client/stdio.py:17`)
- `HttpMcpClient` — streamableHTTP-Transport (modern) (`client/http.py:15`)
- `SseMcpClient` — SSE-Transport (legacy) (`client/sse.py:15`)

**Validierung (`_validation.py`):**
- `McpValidationError(ValueError)` — Fehlerklasse (`_validation.py:4`)
- `validate_transport()` — nur `stdio|http|sse` erlaubt (`_validation.py:11`)
- `validate_name()` — nicht leer, max 100 Zeichen (`_validation.py:18`)
- `validate_id()` — nicht leer, nur `[A-Za-z0-9_-]`, max 64 Zeichen (`_validation.py:25`)
- `validate_stdio_config()` — `command` Pflicht (String), `args` muss `list[str]`, `env` muss `dict` (`_validation.py:34`)
- `validate(config)` — Dachfunktion: id + name + transport + transport-spezifisch (`_validation.py:48`)

**Quick-Add-Templates (`defaults.py`):**
- `TEMPLATES` — 8 vordefinierte Server-Vorlagen (`defaults.py:12`):
  1. `filesystem` — `npx -y @modelcontextprotocol/server-filesystem {path}`, user_input `path` (Default `$HOME`)
  2. `memory` — `npx -y @modelcontextprotocol/server-memory`, keine Inputs
  3. `sequential-thinking` — `npx -y @modelcontextprotocol/server-sequential-thinking`
  4. `fetch` — `uvx mcp-server-fetch` (Python)
  5. `time` — `uvx mcp-server-time` (Python)
  6. `git` — `uvx mcp-server-git --repository {repo_path}`, user_input `repo_path`
  7. `sqlite` — `uvx mcp-server-sqlite --db-path {db_path}`, user_input `db_path` (Default `/tmp/test.db`)
  8. `github` — `npx -y @modelcontextprotocol/server-github`, env `GITHUB_PERSONAL_ACCESS_TOKEN={token}`, user_input `token` (`secret: True`)
- `get_template(template_id)` (`defaults.py:104`)
- `render(template, inputs)` — füllt `{platzhalter}` in args/env via `str.format(**inputs)` (`defaults.py:108`)

**API-Endpoints (`api/routes/mcp.py`, Prefix `/api/mcp`):**
- `GET /api/mcp/quick-add` — Template-Liste (auth: `require_auth`) (`mcp.py:18`)
- `POST /api/mcp/quick-add` — aus Template anlegen, 201 (auth: `require_admin`) (`mcp.py:24`)
- `GET /api/mcp/servers` — alle Server + Connect-Status (auth) (`mcp.py:44`)
- `POST /api/mcp/servers` — Server anlegen, 201 (admin) (`mcp.py:49`)
- `GET /api/mcp/servers/{server_id}` — einen Server (auth) (`mcp.py:62`)
- `PATCH /api/mcp/servers/{server_id}` — Felder ändern (admin); filtert `None`-Felder weg (`mcp.py:70`)
- `DELETE /api/mcp/servers/{server_id}` — 204; trennt Verbindung VOR dem Löschen (admin) (`mcp.py:81`)
- `POST /api/mcp/servers/{server_id}/connect` — verbinden + Tools listen (admin) (`mcp.py:89`)
- `POST /api/mcp/servers/{server_id}/disconnect` — trennen (admin) (`mcp.py:107`)
- `GET /api/mcp/servers/{server_id}/tools` — Tools listen (auth) (`mcp.py:113`)
- Pydantic-Schemas + Helper: `McpServerCreate`, `McpServerUpdate`, `QuickAddRequest`, `annotate_status()` in `api/routes/_mcp_schemas.py`

**Runner-/Dispatcher-Anbindung:**
- `runner.py:99-103` — pro Session: `mcp_servers = agent.get("mcp_servers", [])`, `mcp_schemas = await mcp_bridge.schemas_for_servers(mcp_servers)`, gemischt in `tool_schemas`, MCP-Tool-Namen kommen in `allowed_tools`
- `dispatcher.py:61-77` — Dispatch: Tool-Name beginnt mit `mcp__` → `mcp_bridge.call()`, Result → `ToolResult`
- `dispatcher.py:17` — `_ERROR_TYPE_PREFIXES = ("Tool-Crash: ", "MCP-Crash: ")` für Error-Klassifikation

### B. MCP-Server-Seite — HydraHive-eigener Server `hydrahive-api` (`mcp-servers/hydrahive-api/`)

**FastMCP-Server `"hydrahive"` mit GENAU 20 Tools** (`server.py:39`, enforced durch `tests/test_server.py:71`):

System (2):
- `hh_status` — Systemstatus/Version via `GET /api/health` (`server.py:44`, impl `tools/system.py:6`)
- `hh_token_stats` — Token-/Kostenstatistik via `GET /api/dashboard` (`server.py:50`, impl `tools/system.py:13`)

Sessions (4):
- `hh_list_sessions(agent_id?, limit=20)` — `GET /api/sessions` (`server.py:58`, impl `tools/sessions.py:6`)
- `hh_get_session(session_id)` — `GET /api/sessions/{id}` (`server.py:64`, impl `tools/sessions.py:19`)
- `hh_get_messages(session_id, limit=50)` — `GET /api/sessions/{id}/messages` (`server.py:70`, impl `tools/sessions.py:26`)
- `hh_send_message(session_id, message)` — `POST /api/sessions/{id}/inject` (SSE, liest nur HTTP-Status) (`server.py:76`, impl `tools/sessions.py:38`)

Agents (3):
- `hh_list_agents()` — `GET /api/agents` (`server.py:84`, impl `tools/agents.py:6`)
- `hh_get_agent(agent_id)` — `GET /api/agents/{id}` (`server.py:90`, impl `tools/agents.py:14`)
- `hh_update_agent(agent_id, field, value)` — `PATCH /api/agents/{id}` mit `{field: value}` (`server.py:96`, impl `tools/agents.py:21`)

Workspace (3):
- `hh_list_projects()` — `GET /api/projects` (`server.py:104`, impl `tools/workspace.py:6`)
- `hh_list_files(project_id, path="")` — `GET /api/projects/{id}/files` (`server.py:110`, impl `tools/workspace.py:14`)
- `hh_read_file(project_id, path)` — `GET /api/projects/{id}/files/read` (read-only, `get_text`) (`server.py:116`, impl `tools/workspace.py:24`)

Datamining (4) — Prefix `hh_dm_`:
- `hh_dm_search(q, event_type?, from_date?, to_date?, limit=50)` — `GET /api/datamining/search` (`server.py:124`, impl `tools/datamining.py:6`)
- `hh_dm_get_session(session_id)` — `GET /api/datamining/sessions/{id}` (`server.py:139`, impl `tools/datamining.py:27`)
- `hh_dm_list_sessions(limit=20)` — `GET /api/datamining/sessions` (entpackt `.sessions`, NICHT `.items`) (`server.py:145`, impl `tools/datamining.py:34`)
- `hh_dm_stats()` — `GET /api/datamining/stats/latest` (`server.py:151`, impl `tools/datamining.py:43`)

AgentLink (4) — Prefix `hh_al_`:
- `hh_al_status()` — `GET /api/agentlink/status` + lokaler WS-Zustand (`server.py:159`, impl `tools/agentlink.py:6`)
- `hh_al_send(to_agent, task_type, description, context?)` — Handoff via `POST /agentlink/api/states` (`server.py:165`, impl `tools/agentlink.py:19`)
- `hh_al_check_inbox()` — drainen der lokalen In-Memory-Inbox-Queue (`server.py:177`, impl `tools/agentlink.py:36`)
- `hh_al_reply(state_id, result)` — Antwort-Handoff via `POST /agentlink/api/states` (`server.py:183`, impl `tools/agentlink.py:42`)

**Helper-Module:**
- `Auth` — JWT-Login (`POST /api/auth/login`) ODER API-Key (`hhk_…`); Token-Refresh; löscht Passwort nach Login (`_auth.py:6`)
- `RestClient` — Async-HTTP-Wrapper mit 401→refresh→retry: `get`, `get_text`, `post`, `post_form_sse`, `patch` (`_rest.py:7`)
- `AgentLinkClient` — WebSocket-Listener (`/agentlink/ws`) + In-Memory-Handoff-Queue, Reconnect mit Exponential-Backoff (`_agentlink.py:12`)

**Env-Vars** (`README.md:61-71`): `HH_BASE_URL`, `HH_USER`, `HH_PASS`, `HH_API_KEY`, `HH_AGENT_ID` (Default `claude-code`), `HH_VERIFY_SSL`

### C. MCP-Server-Seite — Datamining-Server (`mcp-servers/datamining/`)

FastMCP-Server `"datamining"`, **9 Tools** (gegen REST-API, kein DB-Direktzugriff) (`server.py:25`):
- `search(query, event_type?, username?, agent_name?, from_date?, to_date?, semantic=False, limit=20)` (`server.py:66`)
- `semantic_search(...)` — pgvector-Ähnlichkeitssuche (`server.py:107`)
- `get_session(session_id)` — chronologische Events (`server.py:147`)
- `list_sessions(username?, agent_name?, limit=20)` (`server.py:165`)
- `daily_summary(date)` — deterministische Tagesübersicht, kein LLM (`server.py:191`)
- `error_report(from_date, to_date?)` — fehlgeschlagene Tool-Calls gruppiert (`server.py:261`)
- `tool_stats(from_date, to_date?, agent_name?)` — Tool-Nutzungsstatistik (`server.py:307`)
- `timeline(from_date, to_date?, username?, agent_name?, limit=200)` — Sessions nach Tag gruppiert (`server.py:355`)
- `inject_message(session_id, text)` — Supervisor-Inject, sammelt SSE-Antwort, **kein Owner-Check** (`server.py:444`)
- Env-Vars: `HH_BASE_URL`, `HH_TOKEN` ODER `HH_USER`/`HH_PASS`, `HH_VERIFY_SSL` (`server.py:19-23`)

### D. Frontend (`frontend/src/features/mcp/`)

- `McpPage` — 3-Spalten-Layout: Form/QuickAdd links, `CollapsibleSidebar` (Server-Liste) rechts (`McpPage.tsx:10`)
- `McpServerForm` — Detail-/Edit-Form: Name, Description, enabled-Toggle, command/args/env (stdio) bzw. url (http/sse), Tool-Liste; Connect/Disconnect/Save/Delete (`McpServerForm.tsx:15`)
- `_McpServerFormHeader` — Header mit Name-Input + Connect-/Save-/Delete-Buttons (`_McpServerFormHeader.tsx:16`)
- `McpServerList` — Sidebar: Server mit Status-Badge (`live`/`off`), „New"- + „Template"-Buttons, `HelpButton topic="mcp"` (`McpServerList.tsx:14`)
- `McpToolList` — Tool-Grid mit Name + Beschreibung (`McpToolList.tsx:5`)
- `NewMcpServerDialog` — Modal: ID/Name/Transport/command/args/env/url/description (`NewMcpServerDialog.tsx:15`)
- `QuickAddPanel` + `QuickAddForm` — Template-Karten-Grid + Ausfüll-Modal (markiert installierte mit ✓) (`QuickAddPanel.tsx:13`, `:70`)
- `Field` — Helper-Label-Wrapper (`_mcpHelpers.tsx:1`)
- `mcpApi` — API-Client: `list`, `get`, `create`, `update`, `delete`, `connect`, `disconnect`, `tools`, `quickAddTemplates`, `quickAdd` (`api.ts:15`)
- Typen `McpServer`, `McpTool`, `McpServerCreate` (`types.ts`)
- Route `mcp` → `<McpPage />` (`App.tsx:85`)
- Nav-Eintrag `"mcp": "MCP"` (`i18n/locales/{en,de}/nav.json:25`)
- Farb-Token `"/mcp": "fuchsia"` (`shared/colors.ts:25`)
- i18n-Namespace `mcp` registriert (`i18n/index.ts:74,85,108`), Locale-Files `i18n/locales/{en,de}/mcp.json`

### E. Installer

- `installer/modules/87-mcp-servers.sh` — installiert 6 npm-MCP-Pakete + `dev-browser` (Chromium-Sandbox), schreibt Default-`mcp_servers.json` mit 6 Servern (filesystem, git, sqlite[disabled], fetch, sequential-thinking, time)

---

## WIE

### Ablauf 1: Server in der UI anlegen (Quick-Add)
1. `McpPage` lädt beim Mount `mcpApi.list()` → `GET /api/mcp/servers`. Wenn keine Server, zeigt `QuickAddPanel`.
2. `QuickAddPanel` lädt `mcpApi.quickAddTemplates()` → `GET /api/mcp/quick-add` → liefert `defaults.TEMPLATES`.
3. User klickt Karte → `QuickAddForm`-Modal mit `user_inputs` (z.B. Pfad, Token).
4. Submit → `mcpApi.quickAdd(template_id, server_id, inputs)` → `POST /api/mcp/quick-add`.
5. Backend (`mcp.py:24`): `get_template()` → 404 wenn unbekannt; `render(template, inputs)` füllt `{placeholder}`; `config.create(...)`.
6. `config.create` (`config.py:49`): baut cfg-dict, `_validation.validate(cfg)`, Dubletten-ID-Check, `_save_atomic` schreibt `mcp_servers.json`.
7. `annotate_status()` mischt Connect-Status (immer `false` direkt nach Anlegen, da Pool leer).
8. Frontend `handleCreated(id)` → reloadServers + selektiert neuen Server.

### Ablauf 2: Manuell anlegen
`NewMcpServerDialog` → `mcpApi.create()` → `POST /api/mcp/servers` (`mcp.py:49`) → `config.create()`. Form sendet je nach Transport entweder command/args/env (stdio) oder url (http/sse).

### Ablauf 3: Verbinden + Tools laden (UI)
1. `McpServerForm.toggleConnect()` → `mcpApi.connect(id)` → `POST /api/mcp/servers/{id}/connect`.
2. Backend (`mcp.py:89`): `manager.connect(id)` → `manager._build(cfg)` baut den passenden Client; `client.connect()` (stdio: spawnt Subprozess via `stdio_client` + `ClientSession.initialize()`).
3. `manager.list_tools(id)` → `client.list_tools()` → `McpTool[]`. Antwort: `{connected: true, tools: [...]}`.
4. Frontend setzt `tools` und `connected`.
5. `KeyError` → 404, sonstige Exception → 500 `mcp_connection_failed`.

### Ablauf 4: Agent nutzt MCP-Tool (der Kern)
1. Agent-Config hat `mcp_servers: list[str]` (Server-IDs) — gesetzt über Agent-CRUD (`agents.py:99`).
2. Runner-Start (`runner.py:99-103`):
   - `mcp_servers = agent.get("mcp_servers", [])`
   - `mcp_schemas = await mcp_bridge.schemas_for_servers(mcp_servers)`
   - `tool_schemas = schemas_for(local_tools) + mcp_schemas + plugin_schemas`
   - `allowed_tools = local_tools + [s["name"] for s in mcp_schemas]`
3. `schemas_for_servers` (`tool_bridge.py:37`): Cache-Check pro Server (60s); Cache-Miss → `asyncio.gather` parallel `_fetch(sid)`; pro Tool ein Anthropic-Schema `{name: mcp__sid__tool, description, input_schema}`; Failures pro Server geloggt, blockieren andere nicht.
4. Das LLM gibt einen `tool_use` mit Namen `mcp__<server>__<tool>` zurück.
5. `dispatcher.execute_tool` (`dispatcher.py:32`):
   - persistiert `tool_calls`-Record (auch bei Fehler)
   - `tool_name not in allowed_tools` → fail „nicht erlaubt"
   - sonst `startswith("mcp__")` → `mcp_bridge.call(tool_name, args)`
6. `tool_bridge.call` (`tool_bridge.py:83`): `parse_tool_name` → `(server, tool)`; `mcp_manager.call_tool(server, tool, args)`.
7. `manager.call_tool` (`manager.py:117`): `get_or_connect` (lazy, kein Health-Probe); `client.call_tool`; bei Exception → `disconnect` + `connect` (frischer Subprozess) + Retry EINMAL.
8. Client (`stdio.py:66`): `session.call_tool`; rendert content via `render_tool_content`; `McpToolResult{success, content:[{type:text,text}], error}`.
9. Zurück im Dispatcher (`dispatcher.py:72`): `output_text = mcp_res.content[0]["text"]`; → `ToolResult`; `redaction.scrub_result` schwärzt Secrets; `tools_db.finish` persistiert.

### Ablauf 5: Externer Client → HydraHive (hydrahive-api Server)
1. Claude Code startet `python3 server.py` als stdio-MCP-Server mit `HH_*`-Env.
2. `lifespan` (`server.py:31`): `_auth.ensure_token()` (Login oder API-Key) + `_al.start()` (WebSocket-Listener-Task).
3. Tool-Call (z.B. `hh_list_sessions`) → delegiert an `tools/sessions.list_sessions(_rest, …)` → `_rest.get("/api/sessions")`.
4. `RestClient.get` (`_rest.py:14`): `auth.ensure_token`; GET mit Bearer; 401 → `auth.refresh` (löscht Token, re-login) → retry; `r.json()`.
5. Tool-Module fangen ALLE Exceptions ab und geben `{"error", "code"}` zurück statt zu werfen (LLM bekommt strukturierten Fehler).

### Ablauf 6: AgentLink-WebSocket-Inbox (hydrahive-api)
1. `_al.start()` → `_listen_loop` Task (`_agentlink.py:112`).
2. Verbindet `wss://…/agentlink/ws`, sendet `subscribe channel agent:<id>`.
3. Bei `handoff_received` (`_agentlink.py:150`): holt State via `GET /agentlink/api/states/{id}`, legt ihn in `_queue`.
4. `hh_al_check_inbox` → `drain_inbox()` (`_agentlink.py:73`) leert die Queue nicht-blockierend.
5. Reconnect: Exponential-Backoff (1s→30s), **gibt nach 5 Versuchen auf** (`_agentlink.py:133`).

### Zustandsmaschine Connection (alle Transports identisch)
`None` → `connect()` baut `AsyncExitStack` (stdio_client/streamablehttp/sse + ClientSession + initialize) → `_session` gesetzt = `is_connected==True`. Fehler bei Setup → `stack.aclose()` + re-raise (kein Leak). `close()` → `stack.aclose()` (cascading teardown, killt Subprozess) → `_session=None`.

---

## WO

**Client-Layer Core:**
- `core/src/hydrahive/mcp/__init__.py:8` — Re-Export `config, manager, tool_bridge, McpValidationError`
- `core/src/hydrahive/mcp/config.py:15` — `_path()` → `settings.mcp_config`
- `core/src/hydrahive/mcp/config.py:19` `_load_all`, `:30` `_save_atomic`, `:38` `list_all`, `:42` `get`, `:49` `create`, `:90` `update`, `:106` `delete`
- `core/src/hydrahive/mcp/manager.py:26-27` Pool+Lock, `:30` `_build`, `:55` `connect`, `:70` `get_or_connect`, `:83` `disconnect`, `:92` `disconnect_all`, `:99` `status`, `:107` `list_tools`, `:117` `call_tool`
- `core/src/hydrahive/mcp/tool_bridge.py:15-19` Konstanten+Cache, `:22` `make_tool_name`, `:26` `parse_tool_name`, `:37` `schemas_for_servers`, `:58` `_fetch`, `:83` `call`
- `core/src/hydrahive/mcp/_validation.py:4` Exception, `:11/:18/:25/:34/:48` Validatoren
- `core/src/hydrahive/mcp/defaults.py:12` `TEMPLATES`, `:104` `get_template`, `:108` `render`
- `core/src/hydrahive/mcp/client/base.py:8` `McpTool`, `:15` `McpToolResult`, `:22` `McpClient`-Protocol, `:35` `render_tool_content`
- `core/src/hydrahive/mcp/client/stdio.py:17` `StdioMcpClient`, `:37` `connect`, `:53` `list_tools`, `:66` `call_tool`, `:81` `close`
- `core/src/hydrahive/mcp/client/http.py:15` `HttpMcpClient` (`:36-38` Tuple-Unpack `(read, write, get_session_id)`)
- `core/src/hydrahive/mcp/client/sse.py:15` `SseMcpClient`

**API:**
- `core/src/hydrahive/api/routes/mcp.py:15` Router (`prefix=/api/mcp`), `:18/:24/:44/:49/:62/:70/:81/:89/:107/:113` Endpoints
- `core/src/hydrahive/api/routes/_mcp_schemas.py:9/:22/:33` Pydantic-Modelle, `:39` `annotate_status`
- `core/src/hydrahive/api/main.py:40` Import, `:114` `app.include_router(mcp_router)`

**Runner-Integration:**
- `core/src/hydrahive/runner/runner.py:23` Import `mcp_bridge`, `:99-103` Schema-Merge
- `core/src/hydrahive/runner/dispatcher.py:9` Import, `:17` Error-Prefixes, `:61-77` MCP-Dispatch

**Settings/Pfade:**
- `core/src/hydrahive/settings/_paths.py:82-84` `mcp_config` → `config_dir / "mcp_servers.json"`

**Agent-Config (mcp_servers-Feld):**
- `core/src/hydrahive/agents/config.py:33,55` Parameter + Persistenz
- `core/src/hydrahive/agents/_config_utils.py:39` `cfg.setdefault("mcp_servers", [])`
- `core/src/hydrahive/api/routes/_agent_schemas.py:20,44` Pydantic-Felder
- `core/src/hydrahive/api/routes/agents.py:99` Durchreichen

**MCP-Server-Seite:**
- `mcp-servers/hydrahive-api/server.py:39` FastMCP-Singleton, `:31` `lifespan`, `:22-28` Singletons, `:44-186` 20 Tools
- `mcp-servers/hydrahive-api/_auth.py:6` `Auth`, `:22` `ensure_token`, `:49` `refresh`, `:53` `headers`
- `mcp-servers/hydrahive-api/_rest.py:7` `RestClient`, `:14/:25/:38/:49/:61` Methoden
- `mcp-servers/hydrahive-api/_agentlink.py:12` `AgentLinkClient`, `:31` `send_state`, `:56` `reply_to_handoff`, `:73` `drain_inbox`, `:112` `_listen_loop`, `:140` `_handle_message`
- `mcp-servers/hydrahive-api/tools/{system,sessions,agents,workspace,datamining,agentlink}.py`
- `mcp-servers/hydrahive-api/pyproject.toml` (`hydrahive-mcp 0.1.0`, `mcp[cli]>=1.0`, `httpx`, `websockets>=13`)
- `mcp-servers/hydrahive-api/tests/test_server.py:36/:71` 20-Tools-Invariante
- `mcp-servers/datamining/server.py:25` FastMCP `"datamining"`, 9 Tools (`:66`–`:488`)
- `mcp-servers/datamining/pyproject.toml` (`hydrahive-datamining-mcp 1.0.0`)

**Frontend:**
- `frontend/src/features/mcp/McpPage.tsx:10`, `McpServerForm.tsx:15`, `_McpServerFormHeader.tsx:16`, `McpServerList.tsx:14`, `McpToolList.tsx:5`, `NewMcpServerDialog.tsx:15`, `QuickAddPanel.tsx:13/:70`, `_mcpHelpers.tsx:1`, `api.ts:15`, `types.ts:1`
- `frontend/src/App.tsx:12,85` Route
- `frontend/src/shared/colors.ts:25` Farbe
- `frontend/src/i18n/index.ts:74,85,108` + `i18n/locales/{en,de}/mcp.json` + `nav.json:25`

**Installer:**
- `installer/modules/87-mcp-servers.sh:8` Config-Pfad, `:17-24` Pakete, `:60-111` Default-Config

---

## WARUM

**1. Tool-Naming `mcp__<server>__<tool>` ist die einzige Routing-Achse.**
Es gibt keine Registry-Tabelle für welcher Name zu welchem Tool gehört — der Name selbst kodiert Server + Tool. `parse_tool_name` (`tool_bridge.py:26`) und der Dispatcher-Check `startswith(PREFIX)` (`dispatcher.py:61`) hängen daran. **Falle:** Wenn ein Server-ID oder Tool-Name selbst `__` enthält, bricht `split(SEP, 1)`. `split(SEP, 1)` mit `maxsplit=1` heißt: Server-ID darf KEIN `__` enthalten, Tool-Name darf eins (wird nicht weiter gesplittet). Die ID-Validierung (`_validation.py:25`) erlaubt aber einzelne `_` — zwei aufeinander = `__` würde das Routing kaputtmachen. Es gibt keinen expliziten Guard gegen `__` in der ID.

**2. `allowed_tools` ist die Sicherheitsgrenze pro Agent.**
Der Runner baut `allowed_tools = local_tools + [s["name"] for s in mcp_schemas]` (`runner.py:103`). Nur Server, die dem Agent in `mcp_servers` zugewiesen sind, landen in den Schemas UND in `allowed_tools`. Der Dispatcher lehnt jeden Tool-Namen ab, der nicht in `allowed_tools` ist (`dispatcher.py:57`). **Wenn man `mcp_servers` aus der Agent-Config entfernt, verschwinden die Tools sofort** — kein Cache-Bleed, weil `allowed_tools` pro Session frisch gebaut wird. ABER: der `_schema_cache` (60s) cached pro Server-ID global, nicht pro Agent — das ist OK, weil er nur Schemas cached (die sind agent-unabhängig), die Autorisierung passiert separat über `allowed_tools`.

**3. Hybrid-Connection-Modell ohne Health-Probe.**
`get_or_connect` macht bewusst KEINE aktive Probe (`manager.py:70-80`) — der Kommentar erklärt: jeder `list_tools`/`call_tool` reconnectet selbst bei Fehler, das spart einen doppelten `list_tools`-Round-Trip pro Nachricht. Der Reconnect-Pfad (`manager.py:107-114`, `:117-124`) ist „try → bei Exception disconnect + frisch connecten + EINMAL retry". **Falle:** Wenn der Subprozess beim Retry erneut crasht, propagiert die Exception nach oben (nur ein Retry).

**4. Pool ist Prozess-global, nicht user-/agent-scoped.**
`_clients` (`manager.py:26`) ist ein Modul-Singleton. Ein verbundener Filesystem-Server wird von allen Agenten geteilt, die ihn referenzieren. Das ist gewollt (max. 1 Subprozess pro Server), aber bedeutet: ein Server, den ein Agent nutzt, bleibt warm und sichtbar im `/api/mcp/servers`-Status für alle. Connect/Disconnect über die Admin-UI wirkt global.

**5. Zwei verschiedene `tool_bridge`-Module mit gleicher Form.**
`hydrahive.mcp.tool_bridge` (MCP) und `hydrahive.plugins.tool_bridge` (Plugins) haben beide `PREFIX`, `parse_tool_name`, `call`, `schemas_for`. Der Dispatcher unterscheidet per Prefix (`mcp__` vs Plugin-Prefix). Verwechslungsgefahr beim Lesen — sie sind absichtlich parallel gebaut, aber unabhängig.

**6. Der hydrahive-api-Server ist KEIN Core-Code — er spricht REST gegen HydraHive zurück.**
Das ist die SPEC-konforme Architektur (`SPEC.md:980-1066`, „Home Assistant via MCP"): HydraHive exponiert sich als MCP-Server für fremde Clients. Daher: Login über `/api/auth/login`, Tools rufen die öffentliche REST-API. **Invariante:** `HH_AGENT_ID` muss zum AgentLink-Agent passen (vgl. MEMORY: Datamining-Hook braucht agent_id = server-uuid). Der Default `claude-code` ist nur für die Claude-Code-Instanz korrekt.

**7. `Auth` löscht das Passwort nach Login (`_auth.py:47`).**
Bewusst: Credential wird nach erstem Login nicht mehr gebraucht (Token reicht). **Falle:** Wenn der Token abläuft und `refresh()` (`_auth.py:49`) ein Re-Login versucht, ist das Passwort weg → Re-Login schlägt fehl, nur API-Key-Pfad überlebt Token-Ablauf robust. (Refresh setzt `token=""` und ruft `ensure_token`, das ohne Passwort wirft.)

**8. AgentLink-WS gibt nach 5 Versuchen endgültig auf (`_agentlink.py:133`).**
Kein dauerhaftes Reconnect. Wenn AgentLink länger down ist, bleibt die Inbox tot bis Server-Neustart. `hh_al_status` zeigt `ws_connected=False` + `ws_last_error` — der einzige Hinweis.

**9. `delete_server` trennt VOR dem Löschen (`mcp.py:83-86`).**
Reihenfolge wichtig: erst `manager.disconnect` (killt Subprozess + Pool-Eintrag), dann `config.delete`. Umgekehrt bliebe ein verwaister warmer Client im Pool, dessen Config weg ist → `status()` zeigt eine ID, die `config.get` nicht mehr findet. **Es gibt keinen Cleanup von `mcp_servers`-Referenzen in Agent-Configs** beim Löschen eines Servers — ein Agent kann eine tote Server-ID behalten; `schemas_for_servers` loggt dann nur eine Warnung und liefert `[]` für diesen Server (`tool_bridge.py:71-73`).

**10. `schemas_for_servers` schluckt Fehler bewusst (`tool_bridge.py:71`).**
Ein nicht-startbarer MCP-Server (npx-Paket fehlt, Pfad ungültig) blockiert NICHT den ganzen Agent-Run — er bekommt nur dessen Tools nicht. Gut für Robustheit, schlecht für Debugging: der Agent merkt nichts, nur das Server-Log zeigt die Warnung.

---

## Datenmodell

**Persistenz-Datei (Registry):**
- `$HH_CONFIG_DIR/mcp_servers.json` (`settings._paths.py:84`) — JSON `{"servers": [ {server}, … ]}`
- Server-Objekt-Schema (`config.create` `config.py:62-77`):
  - `id: str` (a-z A-Z 0-9 _ -, ≤64), `name: str` (≤100), `transport: "stdio"|"http"|"sse"`, `description: str`, `enabled: bool`, `created_at: iso`, `updated_at: iso`
  - stdio: `command: str`, `args: list[str]`, `env: dict[str,str]`
  - http/sse: `url: str`, `headers: dict[str,str]`
- Geschützte Felder bei `update`: `id`, `created_at` (`config.py:95`)
- Laufzeit-angereichert (nicht persistiert): `connected: bool` via `annotate_status` (`_mcp_schemas.py:39`)

**In-Memory-State (keine DB):**
- `manager._clients: dict[str, McpClient]` — Connection-Pool
- `tool_bridge._schema_cache: dict[str, (float, list[dict])]` — 60s Schema-Cache
- `AgentLinkClient._queue: asyncio.Queue[dict]` — Handoff-Inbox (hydrahive-api)

**Agent-Config-Feld:**
- `mcp_servers: list[str]` (Server-IDs) im Agent-JSON (`agents/config.py:55`, default `[]` via `_config_utils.py:39`)

**Tool-Schema-Format (an LLM):**
- `{name: "mcp__<sid>__<tool>", description: str, input_schema: dict}` (`tool_bridge.py:62-66`); Fallback-Schema `{"type":"object","properties":{}}`

**tool_calls-DB-Records** (geteilt mit allen Tools, `dispatcher.py:50/:99`): MCP-Calls landen in derselben `tool_calls`-Tabelle; Error-Type-Heuristik erkennt `MCP-Crash: <Type>:` (`dispatcher.py:17,20`).

**Env-Vars (hydrahive-api-Server):** `HH_BASE_URL`, `HH_USER`, `HH_PASS`, `HH_API_KEY`, `HH_AGENT_ID`(=claude-code), `HH_VERIFY_SSL`(=0)
**Env-Vars (datamining-Server):** `HH_BASE_URL`(=http://localhost:8000), `HH_TOKEN`, `HH_USER`, `HH_PASS`, `HH_VERIFY_SSL`(=0)

**OAuth-Scope (Anthropic):** `user:mcp_servers` (`oauth/anthropic.py:35`)

---

## Offene Enden

**1. KRITISCHE Schema-Drift Installer ↔ Registry-Loader.**
`installer/modules/87-mcp-servers.sh:60-111` schreibt `mcp_servers.json` als **bare JSON-Array** `[{…}]`. Aber `config._load_all` (`config.py:19-27`) erwartet `{"servers": [...]}` und liest `data.get("servers", [])`. Ein Array hat kein `.get` → wenn `json.loads` ein `list` liefert, knallt `data.get(...)` mit `AttributeError` (NICHT vom `JSONDecodeError`-Except gefangen). **Folge: die vom Installer angelegten Default-Server sind für den Core unsichtbar / führen potenziell zum Crash beim Listen.** Zusätzlich fehlt den Installer-Einträgen das Pflichtfeld `transport` (`grep transport` = 0 Treffer im Script), das `_build` (`manager.py:31`) und `validate` (`_validation.py:51`) brauchen → selbst wenn das Wrapping stimmte, würde `transport == None` zu „Unbekannter Transport" / Validierungsfehler führen. Die Installer-Default-Config ist mit dem aktuellen Code inkompatibel.

**2. `manager.disconnect_all()` ist tot.**
Definiert (`manager.py:92`), aber NIRGENDS aufgerufen (kein Caller im ganzen Core, `api/lifespan.py` referenziert MCP gar nicht). Beim Server-Shutdown werden die stdio-Subprozesse nicht sauber beendet — sie hängen an der `AsyncExitStack`, die ohne expliziten `close()` nur durch Prozess-Ende aufgeräumt wird. Sollte im FastAPI-`lifespan`-Shutdown verdrahtet werden.

**3. Veralteter Phasen-Kommentar.**
`mcp/__init__.py:1-6` sagt „Phase 1: nur stdio … Phase 2 (später): HTTP/SSE". HTTP + SSE sind längst voll implementiert (`client/http.py`, `client/sse.py`, in `_build` verdrahtet). Doku-Drift.

**4. Keine Referenz-Integrität beim Server-Löschen.**
Löscht man einen MCP-Server, bleiben tote Server-IDs in den `mcp_servers`-Listen aller Agenten stehen. Kein Cleanup, kein Warn-Hinweis im UI. Zur Laufzeit harmlos (nur Warnung + leere Schemas), aber stille Inkonsistenz.

**5. `env`-Speicherung im Klartext.**
Quick-Add `github`-Template (`defaults.py:96`) schreibt den PAT als `env.GITHUB_PERSONAL_ACCESS_TOKEN` im Klartext in `mcp_servers.json`. Das `secret: True`-Flag (`defaults.py:98`) wirkt nur im Frontend (Passwort-Input), nicht in der Persistenz. Es gibt keine Verschlüsselung/Redaction für MCP-`env`-Secrets in der Registry — im Gegensatz zum Egress-Redaction-Layer für Tool-Outputs.

**6. Datamining-MCP-Server: README vs. Code-Drift.**
`mcp-servers/datamining/README.md:16-27` dokumentiert eine Config mit `PG_MIRROR_DSN` (Direkt-DB) und nennt nur 3 Tools (`search`, `get_session`, `list_sessions`). Der echte `server.py` ist die „REST API Variante" (Docstring `server.py:2`), nutzt `HH_BASE_URL`/`HH_TOKEN`, und hat 9 Tools inkl. `semantic_search`, `daily_summary`, `error_report`, `tool_stats`, `timeline`, `inject_message`. README beschreibt eine andere (ältere?) Implementierung.

**7. `inject_message` (datamining) und `hh_send_message` (hydrahive-api) ohne Owner-Check.**
`datamining/server.py:448` Docstring: „Kein Owner-Check — funktioniert für jede Session auf diesem Server. Erfordert Admin-Token." Beide MCP-Server können in fremde Sessions injizieren, wenn der Token Admin-Rechte hat. Bewusste Supervisor-Funktion, aber eine breite Angriffsfläche, wenn der Token leakt.

**8. `ha_mcp` (Home Assistant MCP-Endpoint) existiert nur in der SPEC.**
`SPEC.md:980-1073` spezifiziert ausführlich einen `core/src/hydrahive/ha_mcp/`-Server mit `/api/ha-mcp/sse` + `/api/ha-mcp/messages` und Tools `hh_query_memory`, `hh_delegate_to_agent`. **Im Code existiert kein `ha_mcp`-Modul** (`find` = NO ha_mcp). Geplant, nicht gebaut.

**9. `tools/__init__.py` ist leer/1-Zeile** — das `tools`-Package des hydrahive-api-Servers hat keinen `__init__`-Inhalt; Importe gehen über `sys.path` (`from tools.system import …`). Funktioniert nur, weil `server.py` aus dem Package-Root gestartet wird (relative Imports `from _auth import Auth` ohne Package-Präfix). Fragil gegen Start aus anderem CWD.

**10. `McpServerUpdate` lässt `transport`-Wechsel nicht zu**, aber Form sendet bei stdio command/args/env und bei http/sse url — wechselt man den Transport eines bestehenden Servers, bleibt das alte `transport`-Feld stehen und die neuen url/command-Felder passen nicht dazu. Es gibt keinen Transport-Switch in der Edit-Form (`McpServerForm.tsx` zeigt Transport read-only `:88`), nur im New-Dialog. Konsistent, aber unflexibel.

**11. i18n-Key `select_or_new` (`mcp.json:5`) wird im Frontend nicht verwendet** (kein Treffer in den Komponenten) — toter Locale-Key.
