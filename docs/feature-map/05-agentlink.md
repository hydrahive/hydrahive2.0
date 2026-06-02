# AgentLink (Inter-Agent)

> Subsystem für Agent-zu-Agent State-Transfer. **AgentLink selbst ist ein externer Service**
> (`github.com/hydrahive/hydralink`, vom Installer mitinstalliert, PostgreSQL + Redis Pub/Sub).
> HydraHive2 enthält **nur einen Client** dafür: Transport (HTTP/REST + WebSocket),
> Serialisierung, Reconnect, Future-Korrelation. Keine Orchestrierungs- oder State-Logik,
> die in den Service gehört (SPEC.md:48-52, CLAUDE.md „Architektur"-Block).
>
> ZWEI getrennte Client-Implementierungen existieren parallel:
> 1. **Core-Client** (`core/src/hydrahive/agentlink/`) — wird vom Backend-Runner benutzt, treibt das `ask_agent`-Tool und den `handoff_receiver`. Spricht den externen Service direkt an (`HH_AGENTLINK_URL`).
> 2. **MCP-Client** (`mcp-servers/hydrahive-api/_agentlink.py`) — ein eigenständiger, stdio-MCP-Server der die `hh_al_*`-Tools für externe Claude-Code-Instanzen bereitstellt. Spricht das **HH2-Backend** an (`/agentlink/api/...` durch das HH2-Backend zum Service geproxyt — siehe „Offene Enden", Pfad-Drift).

---

## WAS

### Core-Client-Funktionen (`core/src/hydrahive/agentlink/`)

State-CRUD / REST gegen den externen Service:
- `post_state(state) -> State` — POST `/states`, postet einen AgentLink-State (Handoff oder Reply). Sendet `model_dump(exclude_none=True, exclude={"extra"})`. Gibt den vom Service angereicherten State (mit `id`, `created_at`) zurück. `client.py:91`
- `get_state(state_id) -> State | None` — GET `/states/{id}`. 404 → `None`. `client.py:103`
- `list_specialists() -> list[str]` — nur Agent-IDs. Delegiert an `list_specialists_with_meta`. `client.py:113`
- `list_specialists_with_meta() -> list[dict]` — GET `/agents`, mappt Service-Felder auf `{agent_id, name, type, owner, last_seen, online, states}`. `states` wird hart auf `0` gesetzt (nie befüllt). `client.py:144`
- `register_agent(agent_id, name, agent_type?, owner?, meta?)` — POST `/agents`, registriert einen lokalen HH-Agenten im AgentLink-Netz. `client.py:118`
- `heartbeat_agent(agent_id)` — POST `/agents/{id}/heartbeat`, Keepalive. `client.py:137` (definiert, **aber nirgends aufgerufen** — siehe Offene Enden)

Pending-Future-Verwaltung (Korrelation von ask_agent → Reply-State):
- `register_pending(reply_to_state_id, expected_sender="") -> Future` — legt eine wartende Future + erwarteten Absender im Modul-Dict ab. `client.py:46`
- `cancel_pending(reply_to_state_id)` — entfernt + cancelt Future (Timeout/Cancellation). `client.py:52`
- `resolve_pending(reply_to_state_id, response_state) -> bool` — löst Future **nur** wenn Absender matcht (Spoofing-Schutz #184). `client.py:67`
- `pending_handoffs_count() -> int` — Anzahl offener Futures (für Status). `client.py:87`
- `_sender_matches(expected, response) -> bool` — interne Absender-Prüfung (exakt oder Basis-ID vor `/Name`-Suffix). `client.py:58`
- `_auth_headers() -> dict` — Bearer-Header wenn `HH_AGENTLINK_TOKEN` gesetzt. `client.py:40`

WebSocket-Listener (`_ws_listener.py` / `_ws_state.py`):
- `start_listener(on_event)` — startet persistenten WS-Listener-Task (idempotent: kein Doppelstart). `_ws_listener.py:23`
- `stop_listener()` — setzt Stop-Event, wartet 5 s, cancelt sonst. `_ws_listener.py:32`
- `restart_listener()` — Stop + reset last_error + Start (für manuellen Reconnect-Endpoint). `_ws_listener.py:46`
- `listen_loop(on_event, stop)` — die eigentliche Connect/Subscribe/Reconnect-Schleife. `_ws_listener.py:55`
- `is_connected() -> bool` — `_ws_state.py:14`
- `last_error() -> str | None` — `_ws_state.py:10`
- `reconnect_attempts() -> int` — `_ws_state.py:18`
- `last_connect_at() -> str | None` — `_ws_state.py:22`

Protocol-Modelle (`protocol.py`):
- `TaskBlock` — `{type, description, priority=5, status="in_progress"}`. `protocol.py:12`
- `ContextBlock` — `{files: list[dict], git: dict|None, errors: list[str]}`. `protocol.py:19`
- `WorkingMemory` — `{hypotheses, decisions, findings}`. `protocol.py:25`
- `Handoff` — `{to_agent, reason, required_skills}`. `protocol.py:31`
- `State` — Top-Level-Objekt `{agent_id, task, context, working_memory, handoff?, id?, created_at?, knowledge?, extra}`. `protocol.py:43`
- `WSEvent` — Push-Event `{type, state_id?, to_agent?, from_agent?, timestamp?, raw}`. `protocol.py:58`

### Backend-Tool

- **`ask_agent`** (`tools/ask_agent.py`) — das einzige LLM-Tool dieses Subsystems. Beauftragt einen anderen Agenten via AgentLink und **blockiert** bis Antwort/Timeout. `ask_agent.py:248`
  - Parameter: `agent_id` (ID/Name, oder `persona@workstation` für Federation), `task`, `task_type` (`bug_fix|feature|review|research|refactor`, default `feature`), `context` (Keys: `error_log`, `code_snippet`, `related_files`, `files`, `errors`, `git`), `required_skills`.
  - Nur registriert wenn `HH_AGENTLINK_URL` gesetzt ist (`tools/__init__.py:82`). Sonst gar nicht im Toolset (verhindert Stub-Fehler-Loops, #13).
  - Steht in den Default-Toolsets von Master + Project-Agenten (`agents/_defaults.py:11,20`), wird aber zur Laufzeit gefiltert wenn nicht registriert (`agents/_defaults.py:30`).

### MCP-Tools (`hh_al_*`, für externe Claude-Code-Instanzen)

Exponiert vom eigenständigen FastMCP-Server `mcp-servers/hydrahive-api/server.py`:
- **`hh_al_status()`** — AgentLink-Verbindungsstatus + bekannte Agenten. Kombiniert HH2-`/api/agentlink/status` mit lokalem WS-State (`ws_connected`, `ws_last_error`, `inbox_count`, `our_agent_id`). `server.py:159`, `tools/agentlink.py:6`
- **`hh_al_send(to_agent, task_type, description, context?)`** — postet einen Handoff-State. `server.py:165`, `tools/agentlink.py:19`
- **`hh_al_check_inbox()`** — drained die lokale Inbox-Queue (eingegangene `handoff_received`-States). `server.py:177`, `tools/agentlink.py:36`
- **`hh_al_reply(state_id, result)`** — postet einen Reply-State mit `reason="reply_to:{state_id}"`. `server.py:183`, `tools/agentlink.py:42`

### REST-Endpoints (HH2-Backend, `api/routes/agentlink.py`)

- **`GET /api/agentlink/status`** — Voll-Status (configured, connected, ws_connected, backend_reachable, last_error, url, ws_url, agent_id, handoff_timeout_s, known_agents, reconnect_attempts, last_connect_at, pending_handoffs, active_handoffs, dashboard_url). Auth: `require_auth` (jeder eingeloggte User). `agentlink.py:29`
- **`POST /api/agentlink/reconnect`** — manueller Listener-Neustart. Auth: `require_admin`. 400 wenn nicht konfiguriert, 409 wenn Listener nie gestartet. `agentlink.py:64`

### UI-Komponenten (Frontend, System-Seite)

- **`AgentLinkCard`** — Status-Karte: Connect-Indikator, URL/WS-URL/Agent-ID/Timeout, last_connect (relativ), reconnect_attempts (gelb >5), pending_handoffs (amber), last_error, Reconnect-Button (nur Admin, nur wenn disconnected), Dashboard-Link. Pollt `/agentlink/status` alle 10 s. `AgentLinkCard.tsx:13`
- **`AgentLinkKnownAgents`** — Liste bekannter Agenten mit Online-Dot, Name, Typ, last_seen. `_AgentLinkKnownAgents.tsx:9`
- **`_agentLinkHelpers.ts`** — Typen `KnownAgent`, `AgentLinkStatus` + `relTime()`-Helper. `_agentLinkHelpers.ts:1`
- Eingebunden über `SystemPage.tsx` (importiert `AgentLinkCard`). `_SpecialistsTab.tsx` nutzt `allowed_specialists` für Project-Freigaben.

### Config-Flags / Env-Vars (`settings/_services.py`, `_AgentLinkMixin`)

- `HH_AGENTLINK_URL` → `agentlink_url` — REST-Basis-URL. Leer ⇒ Subsystem inaktiv, `ask_agent` nicht registriert. `_services.py:47`
- `HH_AGENTLINK_WS_URL` → `agentlink_ws_url` — explizite WS-URL; leer ⇒ aus REST abgeleitet (`http→ws`, `https→wss`, `+ /ws`). `_services.py:53`
- `HH_AGENTLINK_AGENT_ID` → `agentlink_agent_id` — eigene ID im Netz, default `"hydrahive"`. `_services.py:66`
- `HH_AGENTLINK_TOKEN` → `agentlink_token` — Shared-Secret (Bearer) für REST + WS-Subscribe. Leer ⇒ kein Header. `_services.py:72`
- `HH_AGENTLINK_HANDOFF_TIMEOUT` → `agentlink_handoff_timeout` — ask_agent-Wartezeit in Sekunden, default `600`. `_services.py:81`
- `HH_AGENTLINK_DASHBOARD_URL` → `agentlink_dashboard_url` — URL des AgentLink-SPA (default 9001), nur für UI-Link. `_services.py:86`

MCP-Server-eigene Env-Vars (`mcp-servers/hydrahive-api/`):
- `HH_AGENT_ID` (default `"claude-code"`) — Agent-ID des MCP-Clients. `server.py:26`
- `HH_BASE_URL`, `HH_USER`/`HH_PASS` oder `HH_API_KEY`, `HH_VERIFY_SSL` — Auth gegen HH2-Backend. `_auth.py:15-19`

---

## WIE

### Ausgehender Handoff (ask_agent → blockierendes await)

Trigger: Master/Project-Agent ruft im Tool-Loop `ask_agent(agent_id, task, …)` auf (`ask_agent.py:81`).

1. **Validierung** — `agent_id`/`task` getrimmt, leer ⇒ `ToolResult.fail`. `ask_agent.py:82-87`
2. **Federation-Abzweig** — enthält `agent_id` ein `@`, läuft der Call NICHT über AgentLink sondern über `_execute_federated` → `/remote/chat` an eine registrierte Workstation (`ask_agent.py:90`, `217`). Persona-Routing `persona@workstation`.
3. **Guard** — wenn `agentlink_url` leer ⇒ Fail mit Hinweis (kann real nicht passieren, da Tool dann gar nicht registriert ist; defensiver Doppel-Check). `ask_agent.py:93`
4. **UUID-Normalisierung** — Ziel-Name → UUID via `agents.config.get`/Name-Match. `_is_internal = bool(target_agent)`. Interne Ziele werden auf ihre UUID normalisiert. `ask_agent.py:104-116`
5. **Project-Whitelist** — ist der Aufrufer ein `type=="project"`-Agent, muss `target` in `project.allowed_specialists` stehen, sonst Fail. `ask_agent.py:119-134`
6. **Friendly-Key-Mapping** — `error_log` → `errors[]`, `related_files` → `files[{path}]`, `code_snippet` wird ins `task_description` als Fenced-Block gehängt. `ask_agent.py:137-147`
7. **Caller-Sichtbarkeit** — `caller_al_id = "hydrahive/<Agent-Name>"` (Slash-Suffix) damit der Empfänger den konkreten Agenten sieht statt nur „hydrahive". `ask_agent.py:149-157`
8. **Routing-Trick (zentral!)** — für **interne** Handoffs ist `handoff.to_agent` der eigene `agentlink_agent_id` (damit der Service via `agent:{my_id}`-Channel an UNS pusht), und die echte Ziel-UUID wird im `reason`-Präfix `hh-target:<uuid>|hh-task: …` kodiert. Für **externe** Ziele ist `to_agent` direkt das Ziel. `ask_agent.py:159-177`
9. **POST** — `post_state(state)`; ohne `state.id` in der Antwort ⇒ Fail. `ask_agent.py:180-186`
10. **Future registrieren** — `register_pending(sent.id, routing_target)`. `routing_target` ist der erwartete Absender für den Spoofing-Schutz. `ask_agent.py:189`
11. **Warten** — `asyncio.wait_for(fut, timeout=agentlink_handoff_timeout)`. Timeout ⇒ `cancel_pending` + Fail mit State-ID. Cancellation ⇒ cleanup + re-raise. `ask_agent.py:191-200`
12. **Auswerten** — `response.task.description` + `working_memory.findings` zu einem Text-Output zusammengesetzt. `ask_agent.py:202-214`

### Reply-Korrelation (WS-Listener → Future-Auflösung)

Trigger: externer Service pusht ein `handoff_received`-WSEvent auf den `agent:{my_id}`-Channel.

1. **Listener-Loop** verbindet, subscribt (`{"action":"subscribe","channel":"agent:{my_id}"}` + ggf. `token`), liest Frames. `_ws_listener.py:67-94`
2. Jeder Frame → `WSEvent` → `on_event(event)` (in `lifespan._on_event` gesetzt). `_ws_listener.py:83-94`, `lifespan.py:147`
3. **`_on_event`-Dispatch** (`lifespan.py:147-166`):
   - Nur `type == "handoff_received"` mit `state_id` wird verarbeitet.
   - `get_state(state_id)` lädt den vollen State.
   - Enthält `handoff.reason` ein `reply_to:<id>` ⇒ es ist eine **Antwort** → `resolve_pending(reply_to, state)`.
   - Sonst ⇒ es ist ein **neuer eingehender Handoff** → `handoff_receiver.handle(event)` als Background-Task.
4. **`resolve_pending`** (`client.py:67`): findet die Future per `reply_to_state_id`, prüft `_sender_matches`. Match ⇒ `fut.set_result(state)` (ask_agent wacht auf). Kein Match ⇒ Warnung, Future **bleibt offen** (kein Spoof-DoS), gibt `False`.

### Eingehender Handoff (handoff_receiver → neue Session → Reply)

Trigger: `_on_event` ruft `handoff_receiver.handle(event)` für einen Nicht-Reply-State (`lifespan.py:166`).

1. `get_state(event.state_id)` lädt State; leer/ohne Task ⇒ return. `handoff_receiver.py:30-36`
2. **Ziel bestimmen** — `reason` mit Präfix `hh-target:<uuid>` ⇒ echte UUID extrahieren; sonst `handoff.to_agent`. `handoff_receiver.py:38-45`
3. **`_find_target_agent`** — gibt den Agenten **nur** zurück wenn er existiert UND `status=="active"`. KEIN Fallback auf den Admin-Master (#177). `handoff_receiver.py:82-95`
4. Kein gültiges Ziel ⇒ `_post_error_reply` („Kein gültiger Ziel-Agent") + return. `handoff_receiver.py:47-54`
5. **`_warn_if_unconfirmed`** — loggt Warnung wenn Ziel `require_tool_confirm=False` (auto-exec). `handoff_receiver.py:98-107`
6. **Session anlegen** — `sessions_db.create(agent_id=target, user_id=owner|"admin", title=task[:80], metadata={source:"agentlink", incoming_state_id})`. `handoff_receiver.py:57-63`
7. **Handoff-Record** — `db_agent_handoffs.create(...)` → Zeile in `agent_handoffs` mit Status `running`. `handoff_receiver.py:65-70`
8. **Background-Run** — `_run_and_reply(state, session_id, handoff_db_id)` als Task. `handoff_receiver.py:72-75`
9. **`_run_and_reply`** (`handoff_receiver.py:126`):
   - `_build_user_input(state)` baut den Prompt (Task, Typ, Priorität, Dateien, Fehler, Git, Auftraggeber). `handoff_receiver.py:110`
   - `session_run_guard(session_id)` schützt vor Doppellauf (`SessionAlreadyRunning` ⇒ error). `handoff_receiver.py:136-145`
   - `runner.run(session_id, user_input)` wird gestreamt; alle `.text`-Events akkumuliert, `Error`-Event bricht ab. `handoff_receiver.py:137-142`
   - `_post_reply(state, output, status)` postet Antwort-State mit `handoff.to_agent = my_id`, `reason="reply_to:<incoming.id>"`, `working_memory.findings=[output[:2000]]`. `handoff_receiver.py:157-177`
   - `db_agent_handoffs.update_status(handoff_db_id, status)` setzt `done`/`error` + `completed_at`. `handoff_receiver.py:154`

### Reconnect-Zustandsmaschine (WS-Listener)

`listen_loop` (`_ws_listener.py:55`):
- Kein `agentlink_ws_url` ⇒ idle (`await stop.wait()`).
- Schleife bis `stop.is_set()`: connect (`ping_interval=20, ping_timeout=10`) → `_set_connected(True)` → backoff auf 1.0 reset → subscribe → `reader`-Task + `stop`-Task race via `asyncio.wait(FIRST_COMPLETED)`.
- Bei `ConnectionClosed`/`OSError`/`TimeoutError`: `_set_connected(False)`, `_bump_reconnect()`, `_set_last_error`, warte `backoff` (oder return wenn stop), dann `backoff = min(backoff*2, 60.0)`.
- Bei anderem Exception: gleiches, aber `asyncio.sleep(backoff)` (kein stop-aware wait).
- `_set_connected(True)` setzt beim Flankenwechsel `_last_connect_at` (`_ws_state.py:30`).

### Lifespan-Verdrahtung (`api/lifespan.py`)

- Bei `settings.agentlink_url`: `_on_event` definiert, `start_listener(_on_event)`, Heartbeat-Loop-Task gestartet. `lifespan.py:146-172`
- **Heartbeat-Loop** (`_agentlink_heartbeat_loop`, `lifespan.py:60`): alle 60 s alle aktiven HH-Agenten via `register_agent` (Upsert) im Service registrieren. **Nutzt `register_agent`, NICHT `heartbeat_agent`** — Re-Registrierung dient als Heartbeat.
- Shutdown: `agentlink_stop.set()`, Heartbeat-Task join (3 s timeout), `stop_listener()`. `lifespan.py:212-224`

### MCP-Server-Flow (externe Claude-Code-Instanz)

- Singletons bei Import: `Auth`, `RestClient`, `AgentLinkClient(agent_id=HH_AGENT_ID)`. `server.py:22-28`
- `lifespan`: `_auth.ensure_token()` (Login `/api/auth/login`) + `_al.start()` (WS-Listener-Task), Shutdown `_al.stop()`. `server.py:31-37`
- `AgentLinkClient._listen_loop`: connect `al_ws_url` (`base_url + /agentlink/ws`), subscribe `agent:{agent_id}`, bei `handoff_received` → `rest.get(/agentlink/api/states/{id})` → in `_queue` legen. Reconnect: backoff 1→30 s, **harte Obergrenze 5 Versuche, dann Aufgabe**. `_agentlink.py:112-158`
- `drain_inbox()` leert die Queue; `inbox_size` für Status. `_agentlink.py:73-83`

---

## WO

Core-Client:
- `core/src/hydrahive/agentlink/__init__.py:6` — Re-Export-Fassade aller Public-Symbole.
- `core/src/hydrahive/agentlink/client.py:37` — `_PENDING_FUTURES: dict[str, tuple[Future, str]]` (Modul-globaler State).
- `core/src/hydrahive/agentlink/client.py:40` — `_auth_headers`
- `core/src/hydrahive/agentlink/client.py:46` — `register_pending`
- `core/src/hydrahive/agentlink/client.py:52` — `cancel_pending`
- `core/src/hydrahive/agentlink/client.py:58` — `_sender_matches`
- `core/src/hydrahive/agentlink/client.py:67` — `resolve_pending`
- `core/src/hydrahive/agentlink/client.py:87` — `pending_handoffs_count`
- `core/src/hydrahive/agentlink/client.py:91` — `post_state`
- `core/src/hydrahive/agentlink/client.py:103` — `get_state`
- `core/src/hydrahive/agentlink/client.py:113` — `list_specialists`
- `core/src/hydrahive/agentlink/client.py:118` — `register_agent`
- `core/src/hydrahive/agentlink/client.py:137` — `heartbeat_agent` (tot)
- `core/src/hydrahive/agentlink/client.py:144` — `list_specialists_with_meta`

WS-Listener / State:
- `core/src/hydrahive/agentlink/_ws_listener.py:20` — `OnEvent`-Typalias
- `core/src/hydrahive/agentlink/_ws_listener.py:23` — `start_listener`
- `core/src/hydrahive/agentlink/_ws_listener.py:32` — `stop_listener`
- `core/src/hydrahive/agentlink/_ws_listener.py:46` — `restart_listener`
- `core/src/hydrahive/agentlink/_ws_listener.py:55` — `listen_loop`
- `core/src/hydrahive/agentlink/_ws_listener.py:67` — `websockets.connect(...)`
- `core/src/hydrahive/agentlink/_ws_listener.py:71-74` — Subscribe-Payload (+ Token)
- `core/src/hydrahive/agentlink/_ws_listener.py:105-122` — Reconnect-Backoff
- `core/src/hydrahive/agentlink/_ws_state.py:4` — `_listener_state`-Dict
- `core/src/hydrahive/agentlink/_ws_state.py:5-7` — `_connected`, `_reconnect_attempts`, `_last_connect_at`
- `core/src/hydrahive/agentlink/_ws_state.py:30` — `_set_connected` (setzt last_connect_at bei Flanke)

Protocol:
- `core/src/hydrahive/agentlink/protocol.py:12` `TaskBlock`, `:19` `ContextBlock`, `:25` `WorkingMemory`, `:31` `Handoff`, `:43` `State`, `:58` `WSEvent`

Tool + Receiver:
- `core/src/hydrahive/tools/ask_agent.py:39` — `_SCHEMA`
- `core/src/hydrahive/tools/ask_agent.py:81` — `_execute`
- `core/src/hydrahive/tools/ask_agent.py:159-177` — Routing-Trick (hh-target/reason)
- `core/src/hydrahive/tools/ask_agent.py:217` — `_execute_federated`
- `core/src/hydrahive/tools/ask_agent.py:248` — `TOOL`-Objekt
- `core/src/hydrahive/tools/__init__.py:82-83` — bedingte Registrierung von `ask_agent`
- `core/src/hydrahive/tools/__init__.py:98` — `OPTIONAL_TOOLS` (Validierungs-Toleranz)
- `core/src/hydrahive/runner/handoff_receiver.py:26` — `handle`
- `core/src/hydrahive/runner/handoff_receiver.py:82` — `_find_target_agent` (kein Master-Fallback)
- `core/src/hydrahive/runner/handoff_receiver.py:98` — `_warn_if_unconfirmed`
- `core/src/hydrahive/runner/handoff_receiver.py:110` — `_build_user_input`
- `core/src/hydrahive/runner/handoff_receiver.py:126` — `_run_and_reply`
- `core/src/hydrahive/runner/handoff_receiver.py:157` — `_post_reply`
- `core/src/hydrahive/runner/handoff_receiver.py:180` — `_post_error_reply`

Routes + Lifespan:
- `core/src/hydrahive/api/routes/agentlink.py:26` — `router` (prefix `/api/agentlink`)
- `core/src/hydrahive/api/routes/agentlink.py:29` — `GET /status`
- `core/src/hydrahive/api/routes/agentlink.py:64` — `POST /reconnect`
- `core/src/hydrahive/api/main.py:11,99` — Router-Import + `include_router`
- `core/src/hydrahive/api/lifespan.py:60` — `_agentlink_heartbeat_loop`
- `core/src/hydrahive/api/lifespan.py:146-172` — Listener-Start + `_on_event`
- `core/src/hydrahive/api/lifespan.py:147-166` — `_on_event`-Dispatch
- `core/src/hydrahive/api/lifespan.py:212-224` — Shutdown

DB:
- `core/src/hydrahive/db/agent_handoffs.py:8` — `create`
- `core/src/hydrahive/db/agent_handoffs.py:36` — `update_status`
- `core/src/hydrahive/db/agent_handoffs.py:45` — `list_active`
- `core/src/hydrahive/db/migrations/007_agent_handoffs.sql:1` — Tabelle `agent_handoffs`

Settings:
- `core/src/hydrahive/settings/_services.py:45-88` — `_AgentLinkMixin` (alle 6 Config-Keys)

MCP-Server (externer Client):
- `mcp-servers/hydrahive-api/server.py:24-28` — `AgentLinkClient`-Singleton
- `mcp-servers/hydrahive-api/server.py:159` — `hh_al_status`
- `mcp-servers/hydrahive-api/server.py:165` — `hh_al_send`
- `mcp-servers/hydrahive-api/server.py:177` — `hh_al_check_inbox`
- `mcp-servers/hydrahive-api/server.py:183` — `hh_al_reply`
- `mcp-servers/hydrahive-api/tools/agentlink.py:6-48` — `al_status`/`al_send`/`al_check_inbox`/`al_reply`
- `mcp-servers/hydrahive-api/_agentlink.py:12` — `AgentLinkClient`-Klasse
- `mcp-servers/hydrahive-api/_agentlink.py:23` — `al_rest_base` (= `base_url + /agentlink/api`)
- `mcp-servers/hydrahive-api/_agentlink.py:27` — `al_ws_url` (= `base_url + /agentlink/ws`)
- `mcp-servers/hydrahive-api/_agentlink.py:31` — `send_state`
- `mcp-servers/hydrahive-api/_agentlink.py:56` — `reply_to_handoff`
- `mcp-servers/hydrahive-api/_agentlink.py:112` — `_listen_loop` (max 5 Versuche)
- `mcp-servers/hydrahive-api/_agentlink.py:140` — `_handle_message`
- `mcp-servers/hydrahive-api/_rest.py:7` — `RestClient`
- `mcp-servers/hydrahive-api/_auth.py:15-19` — Auth-Konfig

Frontend:
- `frontend/src/features/system/AgentLinkCard.tsx:13` — `AgentLinkCard`
- `frontend/src/features/system/_AgentLinkKnownAgents.tsx:9` — `AgentLinkKnownAgents`
- `frontend/src/features/system/_agentLinkHelpers.ts:11` — `AgentLinkStatus`-Typ, `:28` `relTime`
- `frontend/src/i18n/locales/{de,en}/federation.json`, `system.json` — Labels (`agentlink.*`)

Tests:
- `core/tests/test_agentlink_response_spoofing.py` — `resolve_pending`-Absender-Prüfung (#184)
- `core/tests/test_agentlink_handoff_security.py` — `_find_target_agent` kein Master-Fallback (#177) + `_auth_headers`
- `mcp-servers/hydrahive-api/tests/test_agentlink.py` — MCP-Client-Tools
- `mcp-servers/hydrahive-api/tests/test_server.py:58-61` — Tool-Registrierung `hh_al_*`

---

## WARUM

- **Externer Service, nur Client hier (Invariante).** SPEC.md:48 + CLAUDE.md verbieten AgentLink-Service-Code im Core. Der gesamte `agentlink/`-Ordner ist reiner Transport. State-Persistenz, Pub/Sub-Routing, Agent-Registry leben im externen `hydralink`-Service (PostgreSQL + Redis). Wer hier State-Logik einbaut, bricht die Architektur-Grenze.

- **Der „hh-target im reason"-Trick (zentral, fragil).** AgentLink routet Pushes über den `agent:{to_agent}`-Channel. Damit der externe Service eine **Antwort** an die richtige HH-Instanz pusht, muss `handoff.to_agent` der eigene `agentlink_agent_id` sein — nicht die interne Agent-UUID. Die echte interne Ziel-UUID wird deshalb in `reason` als `hh-target:<uuid>|...` versteckt (`ask_agent.py:159-177`), weil `extra{}` von `post_state` per `exclude={"extra"}` **nicht** gesendet wird (`client.py:96`). `handoff_receiver` parst dieses Präfix wieder aus (`handoff_receiver.py:42`). Wer `to_agent` oder das `reason`-Format ändert, zerstört das Routing **lautlos** — der Handoff landet beim falschen Agenten oder nirgends. Der lange Kommentar in `protocol.py:35-40` dokumentiert diese Reason-basierte Korrelation.

- **Response-Spoofing-Schutz (#184).** Ein WSEvent mit `reason="reply_to:<id>"` kann von jedem Absender kommen. Ohne Prüfung könnte ein fremder Agent eine wartende `ask_agent`-Future mit beliebigem (prompt-injiziertem) Inhalt auflösen. Deshalb speichert `register_pending` den erwarteten Absender (`routing_target`) und `resolve_pending` akzeptiert nur exakte ID oder Basis-ID vor `/Name`-Suffix (`_sender_matches`, `client.py:58`). **Gotcha/Designentscheid:** bei Mismatch wird die Future **nicht** entfernt — sonst könnte ein Angreifer durch frühes Spoofen die echte Antwort dauerhaft verhindern (Spoof-DoS). Leerer `expected` ⇒ keine Prüfung (Rückwärtskompatibilität).

- **Kein Master-Fallback bei Inbound (#177).** Ein von außen kommender Handoff darf **niemals** auf den unrestricted Admin-Master eskalieren — das wäre eine Remote-Code-Execution-Tür. `_find_target_agent` gibt strikt nur explizit adressierte, **aktive** Agenten zurück, sonst `None` → Error-Reply (`handoff_receiver.py:82-95`). Der Test `test_unaddressed_handoff_is_rejected` verifiziert sogar, dass die Master-Liste gar nicht erst geladen wird.

- **`HH_AGENTLINK_TOKEN` ist Transport-Hygiene, nicht die Sicherheitsgrenze.** Der Token geht als Bearer auf alle REST-Calls + WS-Subscribe (`client.py:40`, `_ws_listener.py:72`). Die **harte** Inbound-Garantie ist aber der fehlende Master-Fallback im Receiver, nicht der Token (Kommentar `_services.py:71-78`).

- **`ask_agent` nur registriert wenn konfiguriert (#13).** Ein immer-fehlschlagendes Stub-Tool triggert die Loop-Detection des Runners und verbrennt Iterationen. Deshalb wird `ask_agent` bei leerem `HH_AGENTLINK_URL` gar nicht ins Toolset gelegt (`tools/__init__.py:82`). `OPTIONAL_TOOLS` toleriert es trotzdem in alten Agent-Configs auf Validierungsebene, damit das Entfernen der URL keine Configs zerschießt (#78).

- **`handoff_receiver` liegt in `runner/`, nicht in `agentlink/` (#186).** Bewusst verschoben: das Annehmen eines Handoffs, Session-Anlage und Runner-Start ist **Orchestrierung**, kein Transport. Der `agentlink/`-Ordner bleibt dadurch reiner Client. Wer Empfangslogik zurück nach `agentlink/` zieht, vermischt die Schichten wieder.

- **Heartbeat = Re-Registrierung.** Der Loop ruft `register_agent` (POST `/agents`, Upsert) alle 60 s statt `heartbeat_agent` (`lifespan.py:70`). Funktioniert, weil der Service `last_seen`/`online` beim Re-Register aktualisiert. `heartbeat_agent` (`client.py:137`) ist dadurch toter Code.

- **`ask_agent` blockiert synchron** bis zu 600 s (`agentlink_handoff_timeout`). Ein Tool-Call hält den Runner-Turn so lange. Bei tiefen Handoff-Ketten kann das addieren.

- **Federation-Abzweig in `ask_agent`.** `persona@workstation` umgeht AgentLink komplett und geht über `/remote/chat` (`ask_agent.py:90,217`). AgentLink und Federation sind zwei verschiedene Inter-Agent-Pfade, die sich dieses eine Tool teilen.

- **Zwei Clients, zwei Wahrheiten beim Connect-Status.** Der UI-`connected`-Wert ist `is_connected() OR backend_reachable` (`agentlink.py:47`) — d.h. die Karte zeigt „verbunden" auch wenn nur der `/docs`-Reachability-Check klappt, der WS aber tot ist. Deshalb gibt es daneben das genauere `ws_connected`.

---

## Datenmodell

### Tabelle `agent_handoffs` (SQLite Core, Migration 007)

| Spalte | Typ | Bedeutung |
|---|---|---|
| `id` | TEXT PK | uuid7 |
| `incoming_state_id` | TEXT NOT NULL | AgentLink-State-ID des eingehenden Handoffs |
| `from_agent` | TEXT NOT NULL | Absender-Agent-ID (AgentLink) |
| `agent_id` | TEXT NOT NULL | lokaler Ziel-Agent (UUID) |
| `session_id` | TEXT NOT NULL | erzeugte HH-Session |
| `status` | TEXT DEFAULT 'running' | `running` → `done`/`error` |
| `started_at` | TEXT NOT NULL | ISO-Zeit |
| `completed_at` | TEXT NULL | gesetzt bei != running |

Nur eingehende Handoffs werden getrackt. Ausgehende `ask_agent`-Calls leben nur als In-Memory-Future (`_PENDING_FUTURES`), nicht in der DB.

### In-Memory-State (flüchtig, prozesslokal)

- `_PENDING_FUTURES: dict[str, (Future, expected_sender)]` (`client.py:37`) — geht bei Backend-Restart verloren ⇒ laufende ask_agent-Calls verwaisen.
- `_listener_state`, `_connected`, `_reconnect_attempts`, `_last_connect_at` (`_ws_state.py:4-7`).
- MCP-Client: `asyncio.Queue` Inbox + `_connected`/`_last_error` (`_agentlink.py:17-20`).

### AgentLink-State-Schema (extern, hier als Pydantic-Subset modelliert)

`State{agent_id, task{type,description,priority,status}, context{files,git,errors}, working_memory{hypotheses,decisions,findings}, handoff{to_agent,reason,required_skills}, id, created_at, knowledge, extra}` (`protocol.py:43`). `extra` ist passthrough, wird beim POST **nicht** gesendet.

### WSEvent

`{type, state_id, to_agent, from_agent, timestamp, raw}` (`protocol.py:58`). Relevanter `type`: `handoff_received` (Core verarbeitet nur diesen). MCP-Client ignoriert zusätzlich `connected`/`subscribed`.

### Config-Keys / Env-Vars

Core: `HH_AGENTLINK_URL`, `HH_AGENTLINK_WS_URL`, `HH_AGENTLINK_AGENT_ID` (default `hydrahive`), `HH_AGENTLINK_TOKEN`, `HH_AGENTLINK_HANDOFF_TIMEOUT` (default 600), `HH_AGENTLINK_DASHBOARD_URL`.
MCP-Server: `HH_AGENT_ID` (default `claude-code`), `HH_BASE_URL`, `HH_USER`/`HH_PASS`/`HH_API_KEY`, `HH_VERIFY_SSL`.

### REST-Endpunkte des externen Service (vom Core-Client genutzt)

`POST /states`, `GET /states/{id}`, `GET /agents`, `POST /agents`, `POST /agents/{id}/heartbeat` (ungenutzt), WS `…/ws` mit `subscribe`-Action auf Channel `agent:{my_id}`.

---

## Offene Enden

- **Pfad-Drift zwischen den zwei Clients.** Der **Core**-Client spricht den externen Service direkt unter `agentlink_url` an (`/states`, `/agents`, `/ws`). Der **MCP**-Client spricht das **HH2-Backend** unter `/agentlink/api/...` bzw. `/agentlink/ws` an (`_agentlink.py:23,27,54`). HH2 mountet aber nur `/api/agentlink/status` und `/api/agentlink/reconnect` (`agentlink.py:26`) — es gibt **keinen** `/agentlink/api/states`- oder `/agentlink/ws`-Endpoint im Core. Damit zeigen `hh_al_send`/`hh_al_reply`/`hh_al_check_inbox` auf Pfade, die das HH2-Backend nicht serviert. Entweder existiert ein nginx-/Proxy-Mapping außerhalb des Repos, oder diese drei MCP-Tools sind aktuell tot. `hh_al_status` funktioniert (geht über das real existierende `/api/agentlink/status`). **Verifizieren bevor man sich auf `hh_al_send` verlässt.**

- **`heartbeat_agent` ist toter Code** (`client.py:137`) — exportiert, aber nirgends aufgerufen; der Heartbeat-Loop nutzt `register_agent`. Kandidat zum Entfernen.

- **`KnownAgent.states` ist immer 0** (`client.py:158`) — hart auf `0` gesetzt, nie aus dem Service befüllt. Das UI-Feld existiert (`_agentLinkHelpers.ts:8`), zeigt aber nie echte Werte.

- **`_PENDING_FUTURES` überlebt keinen Restart.** Läuft ein `ask_agent`-Call und das Backend startet neu, ist die Future weg und die später eintreffende Antwort findet kein Ziel mehr (`resolve_pending` gibt `False`, Antwort-State verpufft). Kein Re-Hydration-Mechanismus.

- **Reconnect-Asymmetrie.** Core-Listener reconnectet **unbegrenzt** (backoff bis 60 s, `_ws_listener.py:115`). MCP-Client gibt nach **5 Versuchen auf** (`_agentlink.py:133`) — danach ist die externe Instanz still ohne AgentLink, bis der MCP-Server neu gestartet wird. Inkonsistente Robustheit.

- **`_handle_message` im MCP-Client verarbeitet nur `handoff_received`** und legt blind den State in die Inbox — **keine** Reply-Korrelation, kein Spoofing-Schutz wie im Core. Eine externe Instanz, die `hh_al_check_inbox` nutzt, sieht jeden gepushten Handoff-State ungeprüft.

- **Doppelte Reconnect-/Backoff-/Subscribe-Logik** in Core (`_ws_listener.py`) und MCP (`_agentlink.py`) — paralleler, leicht divergierender Code (DRY-Bruch, aber bewusst getrennte Deployments).

- **`active_handoffs` im Status nutzt `db_agent_handoffs.list_active()`** ohne Limit (`agentlink.py:59`) — bei vielen `running`-Rows unbounded; in der Praxis klein, aber kein `LIMIT`.

- **`list_active` setzt `conn.row_factory`** auf der geteilten Connection (`agent_handoffs.py:47`) — wenn die Connection wiederverwendet wird, könnte die Row-Factory nachwirken. Prüfen ob `db()` pro Call eine frische Connection liefert.

- **SPEC nennt das Tool `hh_delegate_to_agent`** (SPEC.md:1022) als geplante MCP-Tool-Suite, implementiert ist aber `hh_al_send` + Backend-Tool `ask_agent`. Namens-Drift zwischen SPEC und Code (kein Code-Bug, aber Doku-Inkonsistenz — SPEC ist Tills Domäne, nicht anfassen).
