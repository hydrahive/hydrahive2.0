# Querschnitt: End-to-End-Datenfluss & Glue

> Dieses Dokument tracet EINE User-Nachricht vom Klick im Browser bis zur
> persistierten Antwort und zurück ins UI, und beschreibt die load-bearing
> Verdrahtung, die das Ganze zusammenhält: FastAPI-App-Aufbau, Session-
> Lifecycle, Runner-Loop, LLM-Bridge, Tool-Loop, SSE-Stream, Frontend-State.
> Es ist bewusst exhaustiv. Sammelbegriffe wurden vermieden.

---

## WAS

### Einstiegspunkt / App-Bootstrap

- **`hydrahive.api.main:app`** — die FastAPI-App-Instanz (`core/src/hydrahive/api/main.py:76`). Titel `HydraHive2`, Version `2.0.0`, `lifespan=lifespan`.
- **`run()`** — Python-console-script-Entrypoint (`core/src/hydrahive/api/main.py:176`). Liest `settings.host`/`settings.port`, ruft `uvicorn.run("hydrahive.api.main:app", ...)`. Pointet auf den Import-String, NICHT auf das App-Objekt (war früher der Bug, dass das Script nicht startbar war — #198).
- **`HH_ENABLE_DOCS`** — Env-Flag (`main.py:74`). Schaltet `/api/docs` + `/api/openapi.json` frei (Default: aus → `docs_url=None`).
- **CORS-Middleware** (`main.py:91`) — `allow_origins` aus `HH_CORS_ORIGINS` (comma-separated) oder Default `localhost:5173/5174` + `127.0.0.1:5173`. `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- **`unhandled_exception_handler`** (`main.py:156`) — globaler Exception-Handler: loggt mit `exc_info`, gibt `500 {"detail": {"code": "internal_error"}}` zurück (leakt keine Stacktraces ans Frontend).
- **`/api/health`** (`main.py:165`) — gibt `status/version/commit/update_behind` zurück via `current_status()`.
- **~55 Router** werden via `app.include_router(...)` registriert (`main.py:99-153`). Für diesen Querschnitt relevant: `sessions_router`, `streaming_router`, `auth_router`, `agents_router`. Die restlichen (vms, containers, communication, datamining, butler, …) sind Nachbar-Subsysteme.

### Lifespan / Startup-Tasks (Glue, das laufen muss, damit ein Run überhaupt funktioniert)

- **`lifespan(app)`** (`core/src/hydrahive/api/lifespan.py:86`) — Startup/Shutdown-Contextmanager. Reihenfolge beim Start:
  1. `settings.ensure_dirs()` — Verzeichnisse anlegen.
  2. `init_db()` — SQLite-Migrationen ausführen.
  3. `pg_mirror.init()` — nur wenn `settings.pg_mirror_dsn` gesetzt (PostgreSQL-Datamining-Mirror).
  4. `install_system_defaults()` — System-Skills.
  5. `ensure_admin("admin", initial_pw)` — legt Admin-User an (Passwort aus `HH_INITIAL_ADMIN_PASSWORD` oder random; einmalig in `.admin_initial_password`-Datei mit Mode 0600 geschrieben).
  6. `agent_bootstrap.ensure_master("admin")` + `migrate_tools()` — Master-Agent + Tool-Migration.
  7. `plugin_system.load_all()` — Plugins.
  8. `load_butler_builtins()` — Butler-Registry.
  9. `set_start_time()` — Uptime-Marker.
  10. Hintergrund-Loops: Update-Check, Zahnfee-Scheduler, VM-Reconciler, Container-Reconciler, optional Mail-Watcher, optional AgentLink-WS-Listener + Heartbeat, optional Discord-Adapter, optional WhatsApp-Bridge + Adapter.
- **AgentLink-WS-Listener `_on_event`** (`lifespan.py:147`) — routet `handoff_received`-Events: entweder `resolve_pending` (auf eine wartende `ask_agent`-Antwort) oder `handoff_receiver.handle(event)` (neuer eingehender Handoff). Das ist die Verdrahtung für Agent-zu-Agent-Kommunikation, die parallel zum Chat-Pfad existiert.

### Session-Lifecycle-API (CRUD)

- **`GET /api/sessions`** (`sessions.py:29`, `list_sessions`) — Sessions des eingeloggten Users.
- **`POST /api/sessions`** (`sessions.py:35`, `create_session`) — neue Session; prüft dass `agent_id` existiert; Default-Titel `"Chat mit {agent_name}"`. Status 201.
- **`GET /api/sessions/{session_id}`** (`sessions.py:53`, `get_session`) — einzelne Session, mit Owner-Check.
- **`PATCH /api/sessions/{session_id}`** (`sessions.py:65`, `update_session`) — `title`, `status`, `model_override`, `reasoning_effort`. Override-Felder gehen getrennt über `set_model_override` / `set_reasoning_effort` (read-modify-write auf `metadata`).
- **`DELETE /api/sessions/{session_id}`** (`sessions.py:85`, `delete_session`) — Status 204. Cascade löscht Messages/Tool-Calls/LLM-Calls (FK `ON DELETE CASCADE`).
- **`POST /api/sessions/{session_id}/tool-confirm/{call_id}`** (`sessions.py:97`, `tool_confirm`) — User-Entscheidung `approve`/`deny`; ruft `tool_confirmation.resolve(call_id, decision)`. 404 `no_pending_confirmation` wenn die Future weg ist.

### Message-/Run-API (der eigentliche Chat-Pfad)

- **`GET /api/sessions/{session_id}/messages`** (`sessions_messages.py:31`, `list_messages`) — komplette History für die UI. Spielt `tool_calls.duration_ms` per Reihenfolge-Mapping in tool_use/tool_result-Blocks ein.
- **`GET /api/sessions/{session_id}/tokens`** (`sessions_messages.py:57`, `get_tokens`) — `used` / `context_window` / `compact_threshold` / `model` für die TokenMeter-UI.
- **`POST /api/sessions/{session_id}/compact`** (`sessions_messages.py:79`, `manual_compact`) — manuelle Compaction (triggered_by `manual`).
- **`POST /api/sessions/{session_id}/messages`** (`sessions_messages.py:133`, `post_message`) — **der Haupt-Run-Endpoint**. `multipart/form-data` mit `text` (min_length=1) + optionalen `files`. Liefert `StreamingResponse` (SSE).
- **`POST /api/sessions/{session_id}/messages/{message_id}/resend`** (`sessions_messages.py:106`, `resend_message`) — Edit+Resend: schneidet History ab `message_id` (inklusive) ab, schreibt neuen User-Text, triggert Runner. Nur User-Messages editierbar (`message_not_editable` sonst).
- **`POST /api/sessions/{session_id}/log-cmd`** (`sessions_messages.py:154`, `log_slash_cmd`) — Slash-Command-Output persistieren ohne LLM-Roundtrip. Schreibt User-Msg + Assistant-Msg mit `metadata.source='slash_command'`.
- **`POST /api/sessions/{session_id}/inject`** (`sessions_messages.py:179`, `inject_message`, **admin-only**) — Supervisor-Inject in fremde Session, KEIN Owner-Check, fire-and-forget per `BackgroundTasks`, gibt sofort `{"accepted": true}`. Nutzt dieselben Concurrency-Guards (`is_running` + `session_run_guard`).
- **`POST /api/sessions/{session_id}/log`** (`sessions_messages.py:224`, `log_ingest`) — externer Live-Ingest (Claude-Code-Instanzen), reines Mitschreiben, idempotent über `message_id`. MUSS `async def` sein (sonst kein Event-Loop für `mirror.schedule_message` → Mirror still verworfen).

### Runner-Events (das SSE-Vokabular)

Alle als Dataclasses in `core/src/hydrahive/runner/events.py`, jede hat ein `type`-Literal, das zum SSE-`event:`-Namen wird:

- **`CompactionStart`** (`events.py:7`, `type="compaction_start"`) — Kontext wird komprimiert.
- **`IterationStart`** (`events.py:13`, `type="iteration_start"`, Feld `iteration`) — neue Tool-Loop-Iteration.
- **`MessageStart`** (`events.py:20`, `type="message_start"`) — neue Assistant-Bubble beginnt.
- **`TextDelta`** (`events.py:26`, `type="text_delta"`, Feld `text`) — Streaming-Text-Chunk.
- **`TextBlock`** (`events.py:33`, `type="text"`, Feld `text`) — non-streaming/konsolidierter Text (Fallback-Pfad).
- **`ToolUseStart`** (`events.py:40`, `type="tool_use_start"`, `call_id/tool_name/arguments`) — Agent ruft Tool.
- **`ToolConfirmRequired`** (`events.py:49`, `type="tool_confirm_required"`) — Runner wartet auf User-Bestätigung.
- **`ToolUseResult`** (`events.py:58`, `type="tool_use_result"`, `success/output/error/duration_ms`) — Tool fertig.
- **`Done`** (`events.py:70`, `type="done"`, `message_id/iterations/4×tokens`) — Turn komplett.
- **`Error`** (`events.py:82`, `type="error"`, `message/fatal/metadata`) — fataler Abbruch. `metadata.kind="max_iterations"` triggert den "Weitermachen"-Button.
- **`Event`** Union (`events.py:91`).

### Tools / Tool-Registry (was der Agent aufrufen kann)

- **`REGISTRY`** (`core/src/hydrahive/tools/__init__.py:90`) — `dict[name, Tool]`, gebaut von `_build_registry()` (`__init__.py:48`). Enthält: `shell`, `file_read`, `file_write`, `file_patch`, `web_search`, `fetch_url`, `fhir_data`, `health_data`, `read_memory`, `write_memory`, `search_memory`, `todo`, `send_mail`, `list_projects`, `list_skills`, `load_skill`, `read_scratchpad`, `write_scratchpad`, `analyze_image`, `generate_image`, `generate_music`, `generate_speech`, `generate_video`, `transcribe_audio`, `datamining` (SEARCH/SEMANTIC/TIMELINE/TODAY); bedingt `ask_agent` (nur wenn `settings.agentlink_url`), `web_browser`, `webmin_status`, `webmin_call`.
- **`schemas_for(names)`** (`__init__.py:109`) — Anthropic-Format-Schemas `{name, description, input_schema}`.
- **`OPTIONAL_TOOLS`** (`__init__.py:98`) — toleriert in alten Agent-Configs (`ask_agent`, `web_browser`, entfernte `file_search/dir_list/http_request`, `webmin_*`).
- **MCP-Tools** — über `mcp_bridge.schemas_for_servers(mcp_servers)` (Prefix `mcp_bridge.PREFIX`).
- **Plugin-Tools** — über `plugin_bridge.schemas_for(local_tools)` (Prefix `plugin_bridge.PREFIX`).

### Slash-Commands (Frontend-deterministisch, kein LLM)

In `frontend/src/features/chat/commands.ts`, abgefangen von `isCommand()` (`commands.ts:35`), ausgeführt von `runChatCommand()` (`commands.ts:137`):

- **`/help`** (`commands.ts:149`) — Befehlsliste.
- **`/clear`, `/reset`** (`clearCmd`, `commands.ts:53`) — neue Session, gleicher Agent/Projekt.
- **`/model [name]`, `/models`** (`modelCmd`, `commands.ts:39`) — Modell anzeigen/wechseln (PATCH Agent).
- **`/compact`** (`compactCmd`, `commands.ts:58`) — ruft `chatApi.compact`.
- **`/tokens`** (`tokensCmd`, `commands.ts:64`) — ruft `chatApi.tokens`.
- **`/title <text>`, `/rename`** (`titleCmd`, `commands.ts:74`).
- **`/system`, `/sys`** (`systemCmd`, `commands.ts:81`).
- **`/tools`** (`toolsCmd`, `commands.ts:86`).
- **`/agent`** (`agentCmd`, `commands.ts:92`).
- **`/skills`, `/skillkatalog`** (`skillsCmd`, `commands.ts:100`).
- **`/export`** (`exportCmd`, `commands.ts:119`) — History als Markdown.
- **`/<skillname>`** (Default-Branch, `commands.ts:160`) — wenn der Name ein Skill ist: `sendToAgent` mit Skill-Body (→ echter LLM-Run); sonst Fehler.

### UI-Komponenten (Chat-Surface)

- **`ChatPage`** (`frontend/src/features/chat/ChatPage.tsx:40`) — Top-Level. 3-Panel-Layout (Sessions / Chat / Workspace).
- **`useChat(sessionId)`** (`frontend/src/features/chat/useChat.ts:33`) — der zentrale Chat-State-Hook (`send`, `cancel`, `reload`, `confirmTool` + State).
- **`useChatCompact`** (`useChatCompact.ts`) — manuelle Compaction-Steuerung.
- **`applyStreamEvent`** (`frontend/src/features/chat/_chatStream.ts:22`) — SSE-Event → ChatState-Mutation.
- **`sendMessage`** (`frontend/src/features/chat/api.ts:43`) — async-Generator über den fetch-Stream, yieldet `RunnerEvent`s.
- **`MessageInput`** (`MessageInput.tsx`), **`ChatBubbleThread`** (`_ChatBubbleThread.tsx`), **`ToolConfirmBanner`** (`ToolConfirmBanner.tsx`), **`ChatHeader`** (`_ChatHeader.tsx`), **`TokenMeter`**, **`ModelPicker`**, **`ReasoningEffortPill`**, **`AgentPixelMonitor`** (Tool-Aktivitäts-Visualisierung), **`SessionList`**, **`WorkspacePanel`**, **`FileOverlay`**.
- **`useHydraRuntime`** (`_assistantRuntime.ts:74`) — Adapter auf `@assistant-ui/react` (AssistantRuntimeProvider), reicht `send/cancel` durch.

### Config-Flags pro Agent (steuern den Run)

Aus der Agent-Config gelesen in `runner.run` (`runner.py:98-119`): `tools`, `mcp_servers`, `llm_model`, `compact_model`, `compact_tool_result_limit`, `compact_reserve_tokens`, `compact_threshold_pct`, `compact_max_turns`, `tool_result_max_chars`, `cache_ttl`, `max_iterations`, `disabled_skills`, `longterm_memory`, `is_buddy`, `temperature`, `max_tokens`, `fallback_models`, `require_tool_confirm`, `status`, `owner`.

---

## WIE — der End-to-End-Trace EINER User-Nachricht

### 0. Klick im Browser

`MessageInput.onSend` → `ChatPage.handleSend(text, files)` (`ChatPage.tsx:129`).
- Ist `text` ein Slash-Command (`isCommand`)? → `runChatCommand`; je nach Ergebnis lokal anzeigen (`appendLocal`), persistieren (`chatApi.logCmd`), Session wechseln, oder `sendToAgent` → echter Run.
- Sonst: `await chat.send(text, files)` und danach `loadAll()` + Token-Refresh.

### 1. Frontend `send` — optimistic UI + Stream öffnen

`useChat.send` (`useChat.ts:51`):
1. Baut `userMsg` (image-Blocks aus File-Uploads via `URL.createObjectURL`) und eine leere `liveAssistant`-Message (id-Präfix `live-`).
2. `setState`: hängt beide an `messages`, setzt `busy=true`, `iteration=1`. Bei `resendMessageId` wird die History davor abgeschnitten.
3. Legt `AbortController` an (`abortRef`), iteriert `for await (const ev of sendMessage(...))`.
4. Jedes Event → `applyStreamEvent(ev, blocks, setState)`. Rückgabe `"error"` → return; `"done"` → `await reload()` + return.

### 2. HTTP-Request `sendMessage`

`frontend/src/features/chat/api.ts:43`:
1. Holt JWT aus `useAuthStore`.
2. Baut `FormData` (`text` + `files`).
3. Wählt URL: `/api/sessions/{sid}/messages` ODER (bei echter Resend-ID, keine `local-*`) `/.../messages/{id}/resend`.
4. `fetch(..., { method: POST, Authorization: Bearer, body, signal })`.
5. Bei `!res.ok`: parst `detail`, mappt **409 → "Agent läuft noch – bitte kurz warten"**, sonst `detail.code`. Wirft Error.
6. Liest den Body als Stream: `res.body.getReader()` + `TextDecoder`. Buffert, splittet an `\n\n` (SSE-Frame-Grenze), parsed jeden Frame mit `parseSseFrame` (sammelt `data: `-Zeilen, `JSON.parse`), yieldet das Event.

### 3. Backend-Endpoint → Guarded SSE

`post_message` (`sessions_messages.py:133`):
1. `sessions_db.get(session_id)` → 404 `session_not_found` wenn weg.
2. `check_owner(s, *auth)` → 403 `session_no_access` wenn nicht Owner und nicht Admin (`_sessions_helpers.py:26`).
3. `user_content = await build_user_content(s.agent_id, text, files)` (`_session_msg_helpers.py:15`) — ohne Files: nur `text` (str); mit Files: `process_upload` baut Content-Blocks (Bilder etc.) + `{"type":"text","text":text}` am Ende.
4. `return await sse_run_with_guard(session_id, user_content)` (`_session_msg_helpers.py:39`).

`sse_run_with_guard`:
1. `is_running(session_id)` → **409 `session_already_running`** (Pre-Check vor dem teuren Run).
2. `_guarded_stream()`: `async with session_run_guard(session_id)` (acquire-or-fail), iteriert `runner_run(session_id, user_content)` und yieldet jedes Event. Fängt `SessionAlreadyRunning` (Race zwischen `is_running`-Check und `acquire`) und returnt leise.
3. `sse_run_response(events)` (`_session_msg_helpers.py:27`) → `StreamingResponse(to_sse(events), media_type="text/event-stream")` mit Headern `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no` (verhindert nginx-Pufferung).

`to_sse` (`_sse.py:30`) wickelt jeden Event mit `encode_event` (`_sse.py:8`): `name = event.type`, `payload = asdict(event)`, JSON-Body → Frame `event: {name}\ndata: {json}\n\n`. Exceptions im Stream werden in ein `error`-Event gewandelt (`_sse.py:35`).

### 4. Der Runner-Loop `runner.run`

`core/src/hydrahive/runner/runner.py:64`, async-Generator (`AsyncIterator[Event]`):

**Setup (einmal pro Turn):**
1. `sessions_db.get` → `Error` wenn weg. `agent_config.get` → `Error` wenn Agent verwaist. `agent.status != "active"` → `Error` "deaktiviert".
2. `ensure_workspace(agent)` + `ToolContext(...)` bauen (`runner.py:81`) — `session_id`, `agent_id`, `user_id`, `workspace`, `config`, `project_id`.
3. **`session_start(...)`** (`_sessions.py:59`) — JSON-Session-Datei (separat von der SQLite-Session!), idempotent, speichert `first_prompt[:500]`, `model`, status `active`.
4. System-Prompt-Basis: `agent_config.get_system_prompt` + `with_emote_hint` (nur Buddy bekommt die Hydra-Emote-Tabelle, `_emote_hint.py:46`).
5. Tool-Schemas zusammenstellen: `schemas_for(local_tools)` + MCP-Schemas + Plugin-Schemas; `allowed_tools = local_tools + MCP-Namen` (`runner.py:100-103`).
6. **`messages_db.append(session_id, "user", user_input)`** (`runner.py:105`) — die User-Nachricht in SQLite. (Triggert sofort den PG-Mirror, s.u.)
7. Compaction-Parameter aus Agent-Config; `agent_skills` laden.
8. **Proaktiver Recall** (nur bei `longterm_memory`): `top_cards_for(agent_id, limit=8)` (Recall A, einmal/Session) + bei ≥3 Wörtern Eingabe `search_cards(text, limit=3)` (Recall C, cue-getriggert). Best-effort (`runner.py:121-136`).

**Iterations-Loop `for iteration in range(max_iterations)` (`runner.py:138`):**
1. `yield IterationStart(iteration+1)`.
2. **`prepare_history(...)`** (`_runner_iter.py:28`) — async-Gen: lädt `messages_db.list_for_llm`, prüft `should_compact`; wenn ja: `yield CompactionStart()`, `await compact_session(...)`, History neu laden. Letzter yield ist die History-Liste.
3. **`compose_system_prompts(...)`** (`system_prompt.py:18`) — baut `(stable_system, volatile_system, summary_system)`:
   - **stable** = base + extra + Workspace-Zeile + Skills-Tabelle + (longterm-memory-Hint, der `tool_schemas`/`allowed_tools` in-place erweitert) + Scratchpad-Hint + Recall-A-Cards-Block. **Cache-fähig** (ändert sich nicht innerhalb der Session).
   - **volatile** = Datum (kein Uhrzeit → Cache bricht nur um Mitternacht, #141) + Recall-C-Search-Block.
   - **summary** = `[Bisherige Zusammenfassung]\n{summary}` aus `get_latest_summary`.
4. **Pro-Session-Override re-read** (`runner.py:168`): `sessions_db.get` frisch, `metadata.model_override` und `metadata.reasoning_effort` ziehen. `primary_model = model_override or agent.llm_model`. (Re-Read, damit ein Modell-Switch ohne Server-Restart sofort greift.)
5. **`stream_llm_call(...)`** (`_runner_iter.py:72`) — der LLM-Call:
   - `anth_messages = to_anthropic_messages(heal_orphan_tool_uses(history))` — History heilen + ins API-Format wandeln.
   - Iteriert `call_with_stream_or_fallback`; sammelt das finale `IterationResult` (alle anderen yields = Events ans Frontend).
   - Exception → `errors_log.record`, `session_end(status="abandoned")`, `yield Error`, return.
6. Token-Akkumulation (`runner.py:204`) + **`llm_calls_db.insert`** (`runner.py:212`) — pro Call eine Telemetrie-Zeile (Provider, Modell, Tokens, Cache, stop_reason, total_ms, `cost_micros`). In try/except — Telemetrie-Fehler darf den Run nicht killen.
7. **`messages_db.append(session_id, "assistant", result.blocks, ...metadata)`** (`runner.py:240`) — Assistant-Message persistieren (mit Input/Output/Cache-Tokens, Modell, stop_reason, iteration). `history.append(assistant_msg)`.
8. `tool_uses = extract_tool_uses(result.blocks)` (`context.py:203`).
9. **Abbruch-Pfade:**
   - `stop_reason == "max_tokens"` (`runner.py:254`): offene tool_uses synthetisch schließen (`close_open_tool_uses`), `session_end("abandoned")`, `yield Error` (Antwort abgeschnitten), return.
   - **Keine tool_uses** (`runner.py:264`): Turn fertig. `session_end("completed")`, fire-and-forget `compress_session` (in `errors_log.capture` gewrappt), `yield Done(...)`, return. **← der Happy Path endet hier.**
   - **Loop-Detection** (`runner.py:284`): letzte `LOOP_DETECTION_WINDOW=3` Tool-Signaturen identisch → `close_open_tool_uses`, `session_end("abandoned")`, `yield Error("Loop erkannt")`, return.
10. **`process_tool_uses(...)`** (`_runner_tools.py:22`) — der Tool-Loop (s.u.). Letzter yield ist `result_blocks`.
11. **`messages_db.append(session_id, "user", result_blocks)`** (`runner.py:308`) — Tool-Results als User-Message (Anthropic-Konvention: tool_result-Blocks gehören in eine User-Message). `history.append(tool_msg)`. **→ nächste Iteration.**

**Nach dem Loop (max_iterations ohne Abschluss, `runner.py:311`):**
1. **Pre-Resume-Compaction** (#143): wenn History > 50% Window → einmal `compact_session(triggered_by="max_iterations_resume")`, damit der "Weitermachen"-Resume nicht sofort wieder knallt.
2. `session_end("paused")` + `yield Error(metadata.kind="max_iterations", last_assistant_message=...)`. **"paused" ≠ "abandoned"** — resumable per "Weitermachen"-Button.

### 5. Der LLM-Call `call_with_stream_or_fallback`

`core/src/hydrahive/runner/_call.py:64`:
1. `primary = models[0]`. Versucht **Streaming nur auf dem Primärmodell** (Mid-Stream-Fehler lassen sich nicht zurückrollen).
2. Bis zu 2 Versuche (`for _attempt in range(2)`): iteriert `stream_with_tools` (`llm_bridge_stream.py:21`), mappt rohe Anthropic-Stream-Events:
   - `message_start` → `yield MessageStart()`
   - `text_delta` → `yield TextDelta(text)` (setzt `text_sent=True`)
   - `message_stop` → sammelt `blocks/stop_reason/4×tokens`, `streamed_ok=True`, break.
   - Retry bei transientem Fehler **nur solange noch kein Text gesendet** (sonst Doppel-Text).
3. `StreamingNotSupported` (`llm_bridge_stream.py:17`) → break in den Non-Streaming-Pfad. `CodexModelNotAllowed` → raise.
4. Wenn `streamed_ok`: `yield CallResult(_sanitize_blocks(blocks), ..., model=primary)`, return.
5. **Non-Streaming-Fallback mit Modell-Failover** (`_call.py:138`): `for model in models`: `await call_with_tools(...)` (`llm_bridge.py:13`). Bei Exception: `should_failover(e)` (`_failover.py:25`, Quota/Overload/Auth-Patterns mit Wortgrenzen) und nicht letztes Modell → nächstes probieren; sonst raise. Bei Erfolg: konsolidierten Text als `TextBlock` yielden + `CallResult(..., model=model)`.

**Provider-Routing in `call_with_tools` (`llm_bridge.py:13`)** und `stream_with_tools`:
- MiniMax (`is_minimax_model`) → `minimax_anthropic_call` / `minimax_stream`.
- Claude (`claude-`-Prefix) → OAuth-Token via `resolve_anthropic_token` → `anthropic_call` / `anthropic_stream`.
- `openai-codex/`-Prefix → ChatGPT-Plus-OAuth → `codex_call` / `codex_stream`.
- Alle anderen (OpenAI-API-Key, NVIDIA, Groq, Mistral, Gemini, OpenRouter) → LiteLLM (`litellm_call`). **Streaming wird hier NICHT unterstützt** → `StreamingNotSupported` → Non-Streaming-Pfad.

**Cache-Wiring** in `build_anthropic_kwargs` (`_anthropic_payload.py:83`): delikate Reihenfolge — OAuth-Identity zuerst (ohne `cache_control` außer wenn kein system_prompt), `system_prompt` + `summary_system` MIT `cache_control`, **`volatile_system` OHNE `cache_control` ans Ende** (sonst bricht der Prompt-Cache jeden Tag/Minute), `with_cache_breakpoint` setzt einen Breakpoint auf den letzten Block der letzten Message (`messages.length-1`, aus Claude-Code-Source portiert), `cache_control` nur am letzten Tool. MiniMax bekommt `cache_control` komplett gestrippt (sonst HTTP 500) und system als EIN String.

### 6. Der Tool-Loop `process_tool_uses`

`core/src/hydrahive/runner/_runner_tools.py:22` — async-Gen, `for tu in tool_uses`:
1. `yield ToolUseStart(call_id, tool_name, arguments)`.
2. **Wenn `require_confirm`** (Agent-Flag): `tool_confirmation.register(tu_id)` (Future), `yield ToolConfirmRequired(...)`, `await tool_confirmation.wait(tu_id)` (Timeout 300s → auto-deny). Bei `deny`: `ToolResult.fail("Vom Benutzer abgelehnt")`, `yield ToolUseResult(success=False)`, Result-Block anhängen, `continue` (kein `record_observation`).
3. **`execute_tool(...)`** (`dispatcher.py:32`):
   - `tools_db.create(...)` — Call-Attempt IMMER persistieren (auch bei Validation-Fail).
   - Routing: nicht in `allowed_tools` → fail; MCP-Prefix → `mcp_bridge.call`; Plugin-Prefix → `plugin_bridge.call`; nicht in `REGISTRY` → fail; sonst `REGISTRY[tool_name].execute(args, ctx)`. Alle Exceptions → `ToolResult.fail("Tool-Crash: …")` (Runner crasht nie am Tool).
   - **`redaction.scrub_result(result)`** (`dispatcher.py:96`) — Engstelle: bekannte Secret-Werte aus dem Output schwärzen, BEVOR er in DB/Stream geht.
   - `tools_db.finish(record.id, result=asdict(result), status, duration_ms, error_type, error_message)`.
4. **`record_observation(...)`** (`_observations.py:89`) — Observation für die Compress/Crystallize-Memory-Pipeline (`HOOK_POST_TOOL_USE` / `HOOK_POST_TOOL_FAILURE`).
5. `yield ToolUseResult(success, output, error, duration_ms)`.
6. `to_tool_result_block(...)` (`dispatcher.py:110`) — baut den Anthropic-`tool_result`-Block; hängt `media: [{kind, path/url}]` + `tool_name` an; trunkiert bei `tool_result_max_chars` (markiert `tools_db.mark_truncated`). `media`/`tool_name` werden beim API-Call von `_ANTHROPIC_ALLOWED` weggefiltert.
7. `yield result_blocks` (die fertige Liste).

### 7. SSE zurück ins Frontend → State-Update

`applyStreamEvent` (`_chatStream.ts:22`) mutiert pro Event-Typ:
- `compaction_start` → `compacting=true`.
- `iteration_start` → `iteration=N`.
- `message_start` → `compacting=false`, neuer leerer Text-Block, `updateLive`.
- `text_delta` → an letzten Text-Block anhängen (oder neuen anlegen), `updateLive`.
- `text` → Text-Block pushen, `updateLive`.
- `tool_use_start` → `tool_use`-Block pushen, `updateLive`.
- `tool_confirm_required` → `pendingConfirm` setzen (→ `ToolConfirmBanner` rendert).
- `tool_use_result` → `pendingConfirm` löschen falls passend, `tool_result`-Block pushen, `updateLive`.
- `error` → `error`/`errorKind`/`busy=false`, return `"error"`.
- `done` → `busy=false`, `lastTurnTokens` setzen, return `"done"` → `useChat` ruft `reload()` (lädt die echte persistierte History und ersetzt die `live-`Bubble).

`updateLive` (`_chatStream.ts:8`) ersetzt den Content der letzten `live-`Message immutabel.

### 8. Tool-Confirm-Roundtrip

Wenn `pendingConfirm` gesetzt: User klickt im `ToolConfirmBanner` → `chat.confirmTool("approve"|"deny")` (`useChat.ts:94`) → `chatApi.toolConfirm` → `POST /tool-confirm/{call_id}` (`sessions.py:97`) → `tool_confirmation.resolve(call_id, decision)` (`tool_confirmation.py:29`) setzt die Future → der im Runner wartende `await wait(tu_id)` kehrt zurück → Tool läuft (oder wird denied). **Querverbindung:** zwei HTTP-Requests gleichzeitig offen — der SSE-Stream (POST messages) wartet im Runner, ein separater POST liefert die Entscheidung.

---

## WO — Datei:Zeile

### Backend — App / Routing

- `core/src/hydrahive/api/main.py:76` — `app = FastAPI(...)`
- `core/src/hydrahive/api/main.py:99-153` — Router-Registrierung
- `core/src/hydrahive/api/main.py:156` — `unhandled_exception_handler`
- `core/src/hydrahive/api/main.py:165` — `/api/health`
- `core/src/hydrahive/api/main.py:176` — `run()` console-script
- `core/src/hydrahive/api/lifespan.py:86` — `lifespan(app)`
- `core/src/hydrahive/api/lifespan.py:147` — AgentLink `_on_event`-Router
- `core/src/hydrahive/api/middleware/auth.py:18` — `create_token`
- `core/src/hydrahive/api/middleware/auth.py:36` — `require_auth` (JWT + `hhk_`-API-Keys)
- `core/src/hydrahive/api/middleware/auth.py:53` — `require_admin`
- `core/src/hydrahive/api/middleware/errors.py:21` — `coded(status, code, **params)`

### Backend — Session/Message-Routen

- `core/src/hydrahive/api/routes/sessions.py:25` — `router` (prefix `/api/sessions`), `include_router(messages_router)`
- `core/src/hydrahive/api/routes/sessions.py:35` — `create_session`
- `core/src/hydrahive/api/routes/sessions.py:65` — `update_session` (+model_override/reasoning_effort)
- `core/src/hydrahive/api/routes/sessions.py:97` — `tool_confirm`
- `core/src/hydrahive/api/routes/sessions_messages.py:31` — `list_messages` (+duration-Mapping)
- `core/src/hydrahive/api/routes/sessions_messages.py:57` — `get_tokens`
- `core/src/hydrahive/api/routes/sessions_messages.py:106` — `resend_message`
- `core/src/hydrahive/api/routes/sessions_messages.py:133` — `post_message` ← **Haupt-Run-Endpoint**
- `core/src/hydrahive/api/routes/sessions_messages.py:179` — `inject_message` (admin, BackgroundTask)
- `core/src/hydrahive/api/routes/sessions_messages.py:224` — `log_ingest`
- `core/src/hydrahive/api/routes/_session_msg_helpers.py:15` — `build_user_content`
- `core/src/hydrahive/api/routes/_session_msg_helpers.py:27` — `sse_run_response`
- `core/src/hydrahive/api/routes/_session_msg_helpers.py:39` — `sse_run_with_guard`
- `core/src/hydrahive/api/routes/_sse.py:8` — `encode_event`
- `core/src/hydrahive/api/routes/_sse.py:30` — `to_sse`
- `core/src/hydrahive/api/routes/_sessions_helpers.py:26` — `check_owner`
- `core/src/hydrahive/api/routes/_sessions_helpers.py:31` — `serialize_session`
- `core/src/hydrahive/api/routes/_sessions_helpers.py:62` — `serialize_message`

### Backend — Runner

- `core/src/hydrahive/runner/__init__.py:20` — Re-Export `run`, `MAX_ITERATIONS`
- `core/src/hydrahive/runner/runner.py:64` — `run(session_id, user_input, ...)` ← **Herzstück**
- `core/src/hydrahive/runner/runner.py:105` — User-Message-Append
- `core/src/hydrahive/runner/runner.py:138` — Iterations-Loop
- `core/src/hydrahive/runner/runner.py:212` — `llm_calls_db.insert` (Telemetrie)
- `core/src/hydrahive/runner/runner.py:264` — Happy-Path-Done
- `core/src/hydrahive/runner/runner.py:284` — Loop-Detection
- `core/src/hydrahive/runner/runner.py:311` — Pre-Resume-Compaction
- `core/src/hydrahive/runner/runner.py:45` — `MAX_ITERATIONS`, `:46` `LOOP_DETECTION_WINDOW=3`
- `core/src/hydrahive/runner/concurrency.py:41` — `session_run_guard`
- `core/src/hydrahive/runner/concurrency.py:56` — `is_running`
- `core/src/hydrahive/runner/concurrency.py:65` — `force_release`
- `core/src/hydrahive/runner/events.py:91` — `Event`-Union
- `core/src/hydrahive/runner/_runner_iter.py:28` — `prepare_history`
- `core/src/hydrahive/runner/_runner_iter.py:72` — `stream_llm_call`
- `core/src/hydrahive/runner/_runner_iter.py:17` — `IterationResult`
- `core/src/hydrahive/runner/_call.py:64` — `call_with_stream_or_fallback`
- `core/src/hydrahive/runner/_call.py:31` — `CallResult`
- `core/src/hydrahive/runner/_call.py:52` — `_sanitize_blocks`
- `core/src/hydrahive/runner/_failover.py:25` — `should_failover`
- `core/src/hydrahive/runner/llm_bridge.py:13` — `call_with_tools` (Provider-Routing, non-stream)
- `core/src/hydrahive/runner/llm_bridge_stream.py:21` — `stream_with_tools` (Provider-Routing, stream)
- `core/src/hydrahive/runner/llm_bridge_stream.py:17` — `StreamingNotSupported`
- `core/src/hydrahive/runner/_anthropic_payload.py:83` — `build_anthropic_kwargs` (Cache-Ordering)
- `core/src/hydrahive/runner/_anthropic_payload.py:23` — `with_cache_breakpoint`
- `core/src/hydrahive/runner/_runner_tools.py:22` — `process_tool_uses`
- `core/src/hydrahive/runner/dispatcher.py:32` — `execute_tool`
- `core/src/hydrahive/runner/dispatcher.py:96` — `redaction.scrub_result` (Egress-Schwärzung)
- `core/src/hydrahive/runner/dispatcher.py:110` — `to_tool_result_block`
- `core/src/hydrahive/runner/tool_confirmation.py:23` — `register` / `:29` `resolve` / `:37` `wait`
- `core/src/hydrahive/runner/system_prompt.py:18` — `compose`
- `core/src/hydrahive/runner/system_prompt.py:82` — `_volatile_section` (Datum, kein Uhrzeit)
- `core/src/hydrahive/runner/context.py:8` — `heal_orphan_tool_uses`
- `core/src/hydrahive/runner/context.py:130` — `to_anthropic_messages`
- `core/src/hydrahive/runner/context.py:155` — `_ANTHROPIC_ALLOWED` / `:168` `_BLOCKS_TO_STRIP={"thinking"}`
- `core/src/hydrahive/runner/context.py:203` — `extract_tool_uses`
- `core/src/hydrahive/runner/_runner_helpers.py:7` — `close_open_tool_uses`
- `core/src/hydrahive/runner/_emote_hint.py:46` — `with_emote_hint`

### Backend — DB

- `core/src/hydrahive/db/messages.py:13` — `append` (+`schedule_message`-Mirror)
- `core/src/hydrahive/db/messages.py:72` — `get_latest_summary`
- `core/src/hydrahive/db/messages.py:97` — `delete_from` (Edit+Resend)
- `core/src/hydrahive/db/_messages_llm.py:10` — `list_for_llm` (compaction-aware, UUID7-Sortierung)
- `core/src/hydrahive/db/sessions.py:43` — `create` / `:76` `get` / `:82` `list_for_user`
- `core/src/hydrahive/db/sessions.py:130` — `set_model_override` (`db(immediate=True)`)
- `core/src/hydrahive/db/sessions.py:154` — `set_reasoning_effort`
- `core/src/hydrahive/db/mirror.py:182` — `schedule_message` / `:192` `schedule_session`
- `core/src/hydrahive/db/migrations/001_initial.sql:3/18/30/44` — sessions/messages/tool_calls/session_state
- `core/src/hydrahive/db/migrations/010_llm_calls.sql:5` — llm_calls
- `core/src/hydrahive/db/tools.py:72` — `create` / `:117` `finish` / `:138` `mark_truncated`

### Backend — Tools / Session-Files / Memory

- `core/src/hydrahive/tools/__init__.py:48` — `_build_registry` / `:90` `REGISTRY` / `:109` `schemas_for`
- `core/src/hydrahive/tools/_sessions.py:59` — `session_start` (JSON-File) / `:92` `session_end`
- `core/src/hydrahive/tools/_compress.py:88` — `compress_session`
- `core/src/hydrahive/tools/_observations.py:89` — `record_observation`

### Frontend

- `frontend/src/features/chat/ChatPage.tsx:40` — `ChatPage`
- `frontend/src/features/chat/ChatPage.tsx:129` — `handleSend`
- `frontend/src/features/chat/useChat.ts:33` — `useChat`
- `frontend/src/features/chat/useChat.ts:51` — `send`
- `frontend/src/features/chat/useChat.ts:94` — `confirmTool`
- `frontend/src/features/chat/api.ts:43` — `sendMessage` (SSE-Reader)
- `frontend/src/features/chat/api.ts:95` — `parseSseFrame`
- `frontend/src/features/chat/api.ts:12` — `chatApi` (alle REST-Calls)
- `frontend/src/features/chat/_chatStream.ts:22` — `applyStreamEvent`
- `frontend/src/features/chat/_chatStream.ts:8` — `updateLive`
- `frontend/src/features/chat/commands.ts:137` — `runChatCommand`
- `frontend/src/features/chat/types.ts:52` — `RunnerEvent`-Union (Spiegel der Backend-Events)
- `frontend/src/features/chat/_assistantRuntime.ts:74` — `useHydraRuntime`

---

## WARUM — die nicht-offensichtliche Verdrahtung

### Concurrency-Guard ist In-Memory und Single-Process
`_active: set[str]` + `asyncio.Lock` (`concurrency.py:36`). **Invariante:** höchstens ein `runner.run` pro Session gleichzeitig. Symptom ohne Guard (dokumentiert in `concurrency.py:1-17`): doppelte `turn_in_session=1`-Zeilen in `llm_calls`, parallele Tool-Aufrufe, last-write-wins-Chaos in der History — konkret ~46.5¢ verschenkt durch einen parallelen Sonnet-Call. **Falle:** läuft HH2 je mit mehreren uvicorn-Workern, schützt das Set nicht mehr — dann müsste auf DB-Status (`sessions.status='running'`) umgestellt werden (`concurrency.py:15-17`). Der `is_running`-Pre-Check in `sse_run_with_guard` und das `acquire` im `session_run_guard` haben ein Race-Fenster; das ist bewusst doppelt abgesichert (`SessionAlreadyRunning` wird im Stream gefangen, `_session_msg_helpers.py:59`).

### Zwei Session-Stores parallel (SQLite ≠ JSON)
Es gibt **zwei** Session-Begriffe: die SQLite-`sessions`-Tabelle (Chat-Lifecycle, Owner, Titel, Metadata) UND die JSON-Session-Dateien unter `agents_dir/{agent_id}/sessions/{sid}.json` (`_sessions.py:35`, von der Memory/Observation-Pipeline). `session_start`/`session_end` im Runner schreiben NUR die JSON-Datei; `sessions_db` ist die SQLite-Seite. **Falle:** `status="paused"|"abandoned"|"completed"` aus `session_end` landet in der JSON-Datei, nicht in der SQLite-`sessions.status`-Spalte. Wer SQLite-Status mit Memory-Status verwechselt, sucht lange.

### `paused` vs `abandoned` — der Resume-Mechanismus
`session_end(status="paused")` bei `max_iterations` (`runner.py:330`) ist KEIN Endzustand (`_sessions.py:18-23`). Der Runner yieldet `Error(metadata.kind="max_iterations")`; das Frontend (`ChatPage.tsx:245`) rendert daraufhin den "Weitermachen"-Button, der einfach `handleSend("Weitermachen, …")` schickt — ein normaler neuer Run auf derselben `session_id` mit erhaltener History. `abandoned` (max_tokens, Loop, LLM-Fehler) ist final.

### Cache-Stabilität ist die Architektur-Achse des System-Prompts
Die Trennung stable/volatile (`system_prompt.py`) existiert allein für den Anthropic-Prompt-Cache. **Invariante:** alles Volatile (Datum) muss ans ENDE und OHNE `cache_control`, weil Anthropic den GANZEN System-Block byteweise prüft — ein Zeichen Drift im gecachten Bereich invalidiert den Cache. Hätte man Uhrzeit drin, bräche der Cache jede Minute (#141). Recall-A-Cards gehen in stable (ändern sich nur bei nächtlicher Konsolidierung), Recall-C-Search in volatile (cue-abhängig). **Falle:** wer dem stable-Prompt etwas Veränderliches hinzufügt (z.B. Token-Counter, Live-Status), zerstört die Cache-Hit-Rate für die ganze Session.

### History-Healing ist Pflicht, nicht Kür
`heal_orphan_tool_uses` (`context.py:8`) läuft VOR JEDEM LLM-Call. Anthropic verlangt: jeder `tool_use` muss im nächsten User-Turn ein `tool_result` haben. Bricht ein Turn auf `max_tokens` ab bevor Results persistiert sind, ist die Session "vergiftet" — jeder Folge-Send liefert 400. Drei Schutzschichten: (1) synthetische tool_results für fehlende, (2) `_deduplicate_tool_results` (doppelte ID → 400 "multiple tool_result blocks"), (3) `_strip_orphan_tool_results` (tool_result ohne passenden tool_use, kann durch Compaction-Boundary entstehen). Zusätzlich `close_open_tool_uses` (`_runner_helpers.py:7`), das bei Abbruch-Pfaden echte synthetische Results in die DB schreibt. **Falle:** `thinking`-Blöcke MÜSSEN aus der History gestrippt werden (`_BLOCKS_TO_STRIP`, `context.py:168`) — zurückgeschickte Thinking-Signatures ohne aktiven Extended-Thinking-Mode → 400 "Invalid signature in thinking block" (#79).

### UUID7 als chronologischer Schlüssel
`list_for_llm` (`_messages_llm.py:52`) nutzt `id >= first_kept` statt `created_at >=`, weil zwei Messages denselben `created_at`-Timestamp haben können (gleiche Sekunde). UUID7 sortiert lexikografisch == chronologisch, also ist `id >=` der präzise Cut. **Falle:** wer `created_at`-basiert schneidet, riskiert, die falsche Message am Compaction-Boundary einzuschließen (genau der Bug, gegen den `_strip_orphan_tool_results` absichert).

### Mirror braucht einen laufenden Event-Loop
`mirror.schedule_message` (`mirror.py:182`) ruft `asyncio.get_running_loop().create_task(...)`. Wird `messages.append` aus einem sync-Endpoint im Threadpool aufgerufen, gibt es keinen Loop → `RuntimeError` wird gefangen → der Mirror-Task wird **still verworfen** und nur SQLite bekommt die Nachricht. Genau deshalb ist `log_ingest` (`sessions_messages.py:224`) explizit `async def` (Kommentar `:236-239`). **Falle:** jeder neue Endpoint, der `messages.append` aufruft und das Datamining füttern soll, MUSS async sein.

### Streaming ist Anthropic/MiniMax/Codex-only
LiteLLM-Provider liefern `StreamingNotSupported` → der Run fällt automatisch auf Non-Streaming (`_call.py`). Der User sieht dann keine Token-für-Token-Ausgabe, sondern einen `TextBlock` am Stück. Streaming-Retry ist auf 1 Versuch begrenzt und nur solange `text_sent=False` (sonst Doppel-Text im Browser, `_call.py:121`). **Annahme:** Mid-Stream-Fehler sind nicht zurückrollbar, daher Streaming nur auf dem Primärmodell — Failover passiert ausschließlich im Non-Streaming-Pfad.

### Secrets werden an genau einer Engstelle geschwärzt
`redaction.scrub_result` in `execute_tool` (`dispatcher.py:96`) ist der einzige Punkt, an dem Tool-Output bereinigt wird — egal wie das Secret reinkam (env-Dump, `echo $KEY`, `cat config`). Es passiert BEVOR der Output in `tool_calls` (DB) und in den Stream geht. **Falle:** wer Tool-Output an `execute_tool` vorbei serialisiert, umgeht die Redaction.

### Telemetrie darf den Run nie killen
`llm_calls_db.insert` (`runner.py:212`) und `mark_truncated` (`dispatcher.py:130`) sind in try/except — ein Telemetrie-Fehler loggt nur, statt den teuren Run abzubrechen. Gleiches Prinzip beim `compress_session`-Fire-and-forget (`errors_log.capture`, `runner.py:268`).

### Frontend optimistic UI + reload-on-done
`useChat.send` rendert sofort eine `live-`Bubble und mutiert sie pro `text_delta`. Auf `done` wird `reload()` gerufen — das holt die **echte** persistierte History und ersetzt die optimistische Darstellung (inkl. Durations, finaler Modell-Footer, korrekte Message-IDs). **Falle:** `local-*`-IDs existieren nur im Frontend; bei Resend werden sie zu `undefined` umgesetzt (`api.ts:55`), sonst sucht das Backend eine nicht-existente Message.

### 409 ist ein erwarteter, gut-behandelter Zustand
Browser-Refresh/Network-Hiccup/Modell-Switch reißt den SSE-Stream ab, der Backend-Runner läuft aber weiter. Ein neuer Send trifft auf `is_running` → 409 → Frontend zeigt "Agent läuft noch – bitte kurz warten" (`api.ts:69`). Kein Fehler im engeren Sinn, sondern die Concurrency-Invariante in Aktion.

---

## Datenmodell

### SQLite-Tabellen (Core, `migrations/`)

**`sessions`** (`001_initial.sql:3`): `id` PK, `agent_id`, `project_id`, `user_id`, `title`, `created_at`, `updated_at`, `status` (Default `active`), `metadata` (JSON-String — hält `model_override`, `reasoning_effort`). Indizes: `(agent_id, updated_at DESC)`, `(user_id, updated_at DESC)`.

**`messages`** (`001_initial.sql:18`): `id` PK (UUID7), `session_id` FK `ON DELETE CASCADE`, `role`, `content` (str ODER JSON-Block-Liste), `created_at`, `token_count`, `metadata` (JSON — input/output/cache-tokens, model, stop_reason, iteration; oder `source='slash_command'`). Rolle kann `user|assistant|tool|system|compaction` sein. Index `(session_id, created_at)`. `INSERT OR IGNORE` (Idempotenz über message_id).

**`tool_calls`** (`001_initial.sql:30`): `id` PK, `message_id` FK CASCADE, `tool_name`, `arguments` (JSON), `result` (JSON), `status` (`success|error`), `duration_ms`, `created_at`, `metadata` (u.a. `tool_use_id`, `iteration`, `truncated`). Index `(message_id)`.

**`session_state`** (`001_initial.sql:44`): `(session_id, key)` PK, `value`, `updated_at`, `metadata`. Key-Value-Store pro Session.

**`llm_calls`** (`010_llm_calls.sql:5`): `id` PK, `session_id` FK CASCADE, `created_at`, `agent_id`, `user_id`, `provider`, `model`, `temperature`, `max_tokens`, `reasoning_effort`, `prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `stop_reason`, `ttft_ms` (immer NULL — s. Offene Enden), `total_ms`, `cost_micros` (Integer Mikro-Cents, 1 Cent = 1000 Micros — Drift-stabil für SUM), `turn_in_session`. 5 Indizes (session/created/agent/user/model).

### JSON-Session-Datei (Memory-Pipeline, `_sessions.py`)
`agents_dir/{agent_id}/sessions/{sid}.json` — Felder: `id`, `agent_id`, `project`, `started_at`, `ended_at`, `status` (`active|completed|abandoned|paused`), `observation_count`, `model`, `first_prompt[:500]`, `summary`.

### PostgreSQL-Mirror (`_mirror_ddl.py`, optional via `pg_mirror_dsn`)
`sessions`, `events` (Message-Blöcke exploded + Embeddings), `llm_calls`, `cards` (Recall-Memory), `session_metrics`-View. Embedding-Spalten dynamisch via `ensure_embed_col`.

### SSE-Events (Wire-Format)
Frame: `event: {type}\ndata: {json}\n\n`. Typen: `compaction_start`, `iteration_start`, `message_start`, `text_delta`, `text`, `tool_use_start`, `tool_confirm_required`, `tool_use_result`, `done`, `error`. Frontend-Spiegel: `RunnerEvent` (`types.ts:52`).

### Env-Vars / Settings
- `HH_ENABLE_DOCS` — Swagger an/aus.
- `HH_CORS_ORIGINS` — comma-separated CORS-Origins.
- `HH_HOST` / `HH_PORT` → `settings.host`/`settings.port`.
- `HH_INITIAL_ADMIN_PASSWORD` — initiales Admin-Passwort.
- `settings.pg_mirror_dsn` — aktiviert PG-Mirror (sonst No-op).
- `settings.agentlink_url` — aktiviert `ask_agent`-Tool + WS-Listener + Heartbeat.
- `settings.secret_key`, `settings.jwt_algorithm`, `settings.jwt_expire_minutes` — JWT.
- Channel-Flags: `settings.mail_enabled`, `settings.discord_enabled`, `settings.whatsapp_enabled`, `settings.update_check_enabled`.

### Agent-Config-Keys (Run-Steuerung)
`tools`, `mcp_servers`, `llm_model`, `compact_model`, `compact_tool_result_limit`, `compact_reserve_tokens`, `compact_threshold_pct` (Default `DEFAULT_COMPACT_THRESHOLD_PCT`), `compact_max_turns`, `tool_result_max_chars`, `cache_ttl` (Default `"1h"`), `max_iterations` (Default `DEFAULT_MAX_ITERATIONS`), `disabled_skills`, `longterm_memory`, `is_buddy`, `temperature` (Default 0.7), `max_tokens` (Default `DEFAULT_MAX_TOKENS`), `fallback_models`, `require_tool_confirm`, `status`, `owner`.

### Session-Metadata-Keys (Pro-Session-Override)
`model_override` (gewinnt über `agent.llm_model`), `reasoning_effort` (`low|medium|high|null`).

---

## Offene Enden

- **`ttft_ms` immer NULL.** `llm_calls_db.insert` setzt `ttft_ms=None` (`runner.py:226`), obwohl die Spalte existiert (`010_llm_calls.sql:25`). Time-to-first-token wird nie gemessen, obwohl der Streaming-Pfad (`MessageStart`/erster `TextDelta`) den Messpunkt liefern könnte.
- **Zwei Session-Status-Welten driften potenziell.** SQLite-`sessions.status` (über `PATCH`/`update`) und JSON-`status` (über `session_end`) sind nie synchronisiert. Ein Run kann JSON `paused` sein, während SQLite `active` zeigt. Niemand gleicht sie ab.
- **Concurrency-Guard skaliert nicht über Prozessgrenzen.** Explizit als bekannt markiert (`concurrency.py:15-17`). Bei Multi-Worker-Deployment lautlos kaputt — kein Runtime-Guard, der das verhindert.
- **`force_release` ist exportiert, aber im gezeigten Code ungenutzt.** (`concurrency.py:65`) — gedacht für eine Admin-UI ("Notfall: Lock freigeben"), die im Chat-Pfad nicht auftaucht. Toter/halbverdrahteter Pfad bis eine UI/Route ihn aufruft.
- **`is_running` ist nicht race-safe** (`concurrency.py:56-58`, eigener Kommentar "nur Snapshot"). Wird trotzdem als Pre-Check in `sse_run_with_guard` UND in `inject_message` verwendet. Funktioniert nur, weil der echte Guard (`acquire`) dahinter sitzt; der Pre-Check ist reine UX (sofortiges 409 statt teurem Setup).
- **`session_state`-Tabelle (`001_initial.sql:44`)** taucht im gesamten Chat-/Runner-Pfad nicht auf. Key-Value-Store, der hier nicht genutzt wird — entweder von einem anderen Subsystem (Handoff/AgentLink-State?) oder Legacy.
- **`TextBlock`-Event vs. `text_delta`.** Im Streaming-Pfad kommt nur `text_delta`; `TextBlock` (`type="text"`) entsteht nur im Non-Streaming-Fallback (`_call.py:157`). Das Frontend behandelt beide (`_chatStream.ts:43`), aber der `text`-Pfad ist nur bei LiteLLM-Providern/Failover lebendig — leicht zu übersehen beim Testen (alle Tests mit Claude sehen ihn nie).
- **`log_cmd` schreibt am Mirror-Trigger-Pfad mit, aber als `async def` ohne LLM-Run** — die persistierten Slash-Command-Bubbles (`metadata.source='slash_command'`) gehen über `messages.append` und damit auch in den PG-Mirror. Ob deterministischer Command-Output ins Datamining/Embeddings gehört, ist nicht entschieden (potenzielles Rauschen in der semantischen Suche).
- **`Error.fatal`-Feld wird im Frontend nicht ausgewertet.** `RunnerEvent.error` hat `fatal: boolean` (`types.ts:88`), aber `applyStreamEvent` (`_chatStream.ts:72`) liest nur `message`/`metadata.kind`. Jeder `error` wird als fatal behandelt (`busy=false`, return `"error"`). `fatal=false` existiert im Datenmodell, hat aber keine Wirkung.
- **`AgentPixelMonitor`-Heuristik für `ask_agent`** (`ChatPage.tsx:176`) matcht Ziel-Agenten per `name.toLowerCase().includes(targetId)` — fragile Substring-Logik, die bei ähnlichen Agent-Namen falsch auflösen kann. Rein kosmetisch (Visualisierung), aber driftanfällig.
- **`MAX_ITERATIONS` als Modul-Konstante UND Agent-Override** (`runner.py:43-45`). Der Modul-Default existiert nur für Backwards-Compat; der echte Wert kommt aus `agent.max_iterations`. Wer die Konstante ändert, ändert nichts für konfigurierte Agenten — leichte Falle.
- **`process_upload`-Pfad nur teilweise sichtbar.** `build_user_content` (`_session_msg_helpers.py:15`) ruft `process_upload(f, workspace)` (`_files.py`), dessen Block-Output (Bild/PDF/…) hier nicht im Detail getracet ist — eine Kante des Datenflusses, die für vollständige Bild-Ingest-Doku noch geöffnet werden müsste.
