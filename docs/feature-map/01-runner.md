# Runner & Agent-Loop

> Exhaustive Feature-Landkarte für das Subsystem `runner/`, `agents/`, `compaction/`.
> Stand: Code-Read 2026-06-02. Format `pfad/datei.py:zeile`. Pfade relativ zu
> `core/src/hydrahive/` sofern nicht voll qualifiziert.

---

## WAS

Einzeln aufgelistete Fähigkeiten, Module, Funktionen, Tools, Flags, Events, Config-Keys.

### Runner-Kern (`runner/`)

- **`run(session_id, user_input, *, tool_config, extra_system)`** — `runner/runner.py:64` — Async-Generator, EIN User-Turn = beliebig viele Tool-Iterationen. Einstiegspunkt des gesamten Loops. Yieldet `Event`-Objekte (für SSE).
- **`MAX_ITERATIONS`** (Modul-Default = `DEFAULT_MAX_ITERATIONS` = 16) — `runner/runner.py:45` — Backwards-Compat-Konstante; per-Agent `max_iterations` gewinnt.
- **`LOOP_DETECTION_WINDOW = 3`** — `runner/runner.py:46` — Fenstergröße für die Endlosschleifen-Erkennung (3 identische Tool-Signaturen hintereinander → Abbruch).
- **`_user_text(ui)`** — `runner/runner.py:49` — Zieht reinen Text aus `user_input` (str ODER Content-Block-Liste) für den Recall-C-Cue.
- **`__init__.py` Public-API** — `runner/__init__.py:20` — exportiert `run`, `MAX_ITERATIONS`, `events`, alle Event-Klassen.

### Pre-Iteration-Helfer (`runner/_runner_iter.py`)

- **`IterationResult` (dataclass)** — `runner/_runner_iter.py:17` — Sentinel mit `blocks`, `stop_reason`, `used_model`, 4 Token-Felder. Letzter yield von `stream_llm_call`.
- **`prepare_history(...)`** — `runner/_runner_iter.py:28` — Holt `list_for_llm`-History, prüft `should_compact`, triggert ggf. `compact_session(triggered_by="auto")`, yieldet `CompactionStart` + am Ende die History-Liste.
- **`stream_llm_call(...)`** — `runner/_runner_iter.py:72` — Wrapper um `call_with_stream_or_fallback`; akkumuliert Tokens, yieldet Frontend-Events + final ein `IterationResult`.

### Tool-Loop (`runner/_runner_tools.py`)

- **`process_tool_uses(...)`** — `runner/_runner_tools.py:22` — Pro Iteration: alle `tool_use`-Blöcke abarbeiten. Confirmation einholen (falls `require_confirm`), `execute_tool`, `record_observation`, `to_tool_result_block`. Yieldet Events + final `result_blocks: list[dict]`.

### Helfer (`runner/_runner_helpers.py`)

- **`close_open_tool_uses(session_id, tool_uses, reason)`** — `runner/_runner_helpers.py:7` — Schreibt synthetische `tool_result`-Blöcke (is_error) für unfertige `tool_use`s. Verhindert „Session vergiftet → 400 bei jedem nächsten Send".

### LLM-Call mit Streaming + Fallback (`runner/_call.py`)

- **`CallResult` (dataclass)** — `runner/_call.py:31` — Sentinel: `blocks`, `stop_reason`, 4 Token-Felder, `model` (tatsächlich genutztes Modell bei Failover).
- **`_ALLOWED_FIELDS`** — `runner/_call.py:44` — Whitelist erlaubter Felder pro Block-Typ (text/tool_use/thinking/tool_result).
- **`_sanitize_blocks(blocks)`** — `runner/_call.py:52` — Strippt SDK-only-Felder vor DB-Storage.
- **`call_with_stream_or_fallback(...)`** — `runner/_call.py:64` — Versucht Streaming am Primärmodell (max 2 Versuche, Retry nur solange kein Text gesendet); fällt bei Fehler/`StreamingNotSupported` auf Non-Streaming + Modell-Failover zurück.

### Failover-Erkennung (`runner/_failover.py`)

- **`_FAILOVER_PATTERNS`** — `runner/_failover.py:11` — Regex-Liste mit Wortgrenzen: `401/402/429/529`, `authentication_error`, `invalid api key`, `rate.?limit`, `overloaded/quota/insufficient/capacity`, `credit_balance` (NICHT „credit"), `billing/payment`, `oauth token has expired`.
- **`should_failover(exc)`** — `runner/_failover.py:25` — True wenn Fehlertext einen Modellwechsel rechtfertigt.

### System-Prompt-Komposition (`runner/system_prompt.py`)

- **`compose(base, ...)`** — `runner/system_prompt.py:18` — Baut Tupel `(stable_system, volatile_system, summary_system)`. Erweitert bei `longterm_memory=True` `tool_schemas`+`allowed_tools` in-place um Datamining-Tools (Side-Effect!).
- **`_stable_section(...)`** — `runner/system_prompt.py:54` — base + extra_system (extra zuerst!) + `Workspace: <path>` + Skills-Tabelle.
- **`_volatile_section()`** — `runner/system_prompt.py:82` — Nur Datum (kein Uhrzeit!) → Cache bricht nur um Mitternacht.
- **`_LONGTERM_MEMORY_HINT`** — `runner/system_prompt.py:90` — Hinweis-Text auf `datamining_*`-Tools.
- **`_SCRATCHPAD_HINT`** — `runner/system_prompt.py:98` — angehängt wenn `read_scratchpad` in allowed_tools.
- **`_inject_longterm_memory(...)`** — `runner/system_prompt.py:105` — Fügt `TOOL_SEARCH/TOOL_TODAY/TOOL_TIMELINE` (+`TOOL_SEMANTIC` wenn `embed_model` gesetzt) hinzu.
- **`render_cards_block(cards)`** — `runner/system_prompt.py:131` — Recall A: „## Erinnerungen (automatisch verdichtet)"-Block für den gecachten Stable-Prompt.
- **`render_search_block(cards)`** — `runner/system_prompt.py:152` — Recall C: cue-getriggerte Treffer für den volatile Block, mit session-id-Referenz.

### Emote-Hint (`runner/_emote_hint.py`)

- **`EMOTE_NAMES`** — `runner/_emote_hint.py:13` — Liste ~150 Emote-Namen (`smile`, `grin`, …, `popcorn`), spiegelt `frontend/src/features/chat/hydraEmotes.ts`.
- **`HYDRA_EMOTE_HINT`** — `runner/_emote_hint.py:35` — „## Hydra-Emotes"-Block mit Syntax `:hydra-NAME:`.
- **`with_emote_hint(base_prompt, *, is_buddy)`** — `runner/_emote_hint.py:46` — Hängt Emote-Hint NUR bei Buddy-Agenten an (zur Laufzeit, nicht in editierbaren Prompt gebacken).

### Context-/History-Heilung (`runner/context.py`)

- **`heal_orphan_tool_uses(history)`** — `runner/context.py:8` — Injiziert synthetische `tool_result`s für `tool_use`s ohne Antwort; strippt verwaiste `tool_result`s; dedupliziert. Mutiert DB NICHT.
- **`_deduplicate_tool_results(history)`** — `runner/context.py:68` — Entfernt doppelte `tool_result`-Blöcke (gleiche `tool_use_id`) — verhindert „multiple tool_result blocks with id X".
- **`_strip_orphan_tool_results(history)`** — `runner/context.py:94` — Entfernt `tool_result`s ohne passendes vorheriges `tool_use` (Compaction-Boundary-Edge-Case).
- **`to_anthropic_messages(history)`** — `runner/context.py:130` — DB-Messages → Anthropic-API-Format. System-Messages werden übersprungen.
- **`_ANTHROPIC_ALLOWED`** — `runner/context.py:155` — Whitelist erlaubter Felder (text/image/tool_use/tool_result). Strippt `media`/`tool_name`.
- **`_BLOCKS_TO_STRIP = {"thinking"}`** — `runner/context.py:168` — Thinking-Blöcke werden NIE zurück an die API geschickt (sonst „Invalid signature in thinking block" 400, Issue #79).
- **`_sanitize_block(b)`** — `runner/context.py:171` — Einzelblock-Sanitizer, returnt None für Strip-Blöcke.
- **`_normalize_content(content)`** — `runner/context.py:184` — String durchreichen, Listen sanitisieren.
- **`merge_text_blocks(blocks)`** — `runner/context.py:197` — Text-Blöcke joinen (Display/Logging).
- **`extract_tool_uses(blocks)`** — `runner/context.py:203` — Filter auf `tool_use`-Blöcke.

### LLM-Bridge — Provider-Routing (`runner/llm_bridge.py`)

- **`call_with_tools(...)`** — `runner/llm_bridge.py:13` — EIN non-streaming LLM-Call mit Tool-Support. Routing nach Modell:
  - MiniMax (`is_minimax_model`) → `minimax_anthropic_call`
  - `claude-*` (nach `_strip_provider_prefix`) → `anthropic_call` (OAuth-Token via `resolve_anthropic_token`)
  - Prefix `openai-codex/` → `codex_call` (OAuth via `resolve_openai_codex_token`)
  - Alles andere (OpenAI/NVIDIA/Groq/Mistral/Gemini/OpenRouter) → `litellm_call` (nach `apply_keys`)

### LLM-Bridge — Streaming-Routing (`runner/llm_bridge_stream.py`)

- **`StreamingNotSupported(RuntimeError)`** — `runner/llm_bridge_stream.py:17` — Vom Caller gefangen → Non-Streaming-Fallback.
- **`stream_with_tools(...)`** — `runner/llm_bridge_stream.py:21` — Streaming nur für Anthropic + MiniMax + OpenAI-Codex. Alles andere wirft `StreamingNotSupported`.

### Backends Non-Streaming (`runner/_llm_bridge_backends.py`)

- **`anthropic_call(...)`** — `runner/_llm_bridge_backends.py:23` — Direkter Anthropic-SDK-Call. Temperature-Retry bei „deprecated"-400.
- **`minimax_anthropic_call(...)`** — `runner/_llm_bridge_backends.py:63` — Anthropic-SDK gegen `api.minimax.io/anthropic` (Bearer-Header, kein Identity-Block).
- **`_is_tool_use_unsupported(exc)`** — `runner/_llm_bridge_backends.py:107` — Erkennt „Modell unterstützt kein Tool-Use" (NVIDIA NIM etc.).
- **`litellm_call(...)`** — `runner/_llm_bridge_backends.py:122` — OpenAI-kompatible Provider via LiteLLM. Bei Tool-Use-Unsupported: Retry OHNE tools. `timeout=120` hard-cap.

### Anthropic-Payload-Bau (`runner/_anthropic_payload.py`) — SSOT für Stream + Non-Stream (#200)

- **`cache_control(ttl)`** — `runner/_anthropic_payload.py:16` — `{"type":"ephemeral"}` + `ttl` wenn ≠ "5m".
- **`with_cache_breakpoint(messages, ttl)`** — `runner/_anthropic_payload.py:23` — Markiert letzten Content-Block der LETZTEN Message als Cache-Breakpoint (Quelle: claude.ts:3089).
- **`block_to_dict(block)`** — `runner/_anthropic_payload.py:56` — SDK-Objekt → Plain-Dict, vier Stufen (model_dump → dict → dict → json-fallback).
- **`strip_minimax_cache_control(messages, tools)`** — `runner/_anthropic_payload.py:69` — Entfernt `cache_control` (MiniMax → HTTP 500).
- **`build_anthropic_kwargs(...)`** — `runner/_anthropic_payload.py:83` — Baut (Client, kwargs). Delikate Cache-Ordering: OAuth-Identity → system+summary (mit cache_control) → volatile (OHNE cache_control) → Breakpoint auf letzter Message → cache_control nur am letzten Tool. Ruft `apply_effort`.
- **`build_minimax_kwargs(...)`** — `runner/_anthropic_payload.py:137` — System als EIN String (Array bricht nach Compaction), cache_control entfernt.

### Streaming-Provider (`runner/_stream_providers.py`)

- **`_map_event(ev)`** — `runner/_stream_providers.py:15` — Anthropic-SDK-Stream-Event → normalisiertes Dict (`message_start`/`block_start`/`text_delta`/`input_delta`/`block_stop`). `thinking_delta` wird verworfen.
- **`anthropic_stream(...)`** — `runner/_stream_providers.py:43` — Streamt via `client.messages.stream`; temperature-Retry nur vor erstem Event (`yielded` Flag).
- **`minimax_stream(...)`** — `runner/_stream_providers.py:95` — MiniMax-Streaming, kein temperature-Retry.

### Codex-Provider (`runner/_codex_provider.py`)

- **`CodexModelNotAllowed(Exception)`** — `runner/_codex_provider.py:26` — ChatGPT-Account hat keinen Modellzugriff (nicht failover-würdig — wird raised).
- **`CODEX_URL = "https://chatgpt.com/backend-api/codex/responses"`** — `runner/_codex_provider.py:22`
- **`_build_payload(...)`** — `runner/_codex_provider.py:36` — Responses-API-Payload (`store:False`, `stream:True`, `include:["reasoning.encrypted_content"]`).
- **`_headers(...)`** — `runner/_codex_provider.py:57` — `Authorization`, `chatgpt-account-id`, `OpenAI-Beta: responses=experimental`, `originator: hydrahive`.
- **`_parse_sse_line(line)`** — `runner/_codex_provider.py:67`
- **`codex_stream(...)`** — `runner/_codex_provider.py:79` — SSE-Parsing von `response.output_text.delta` / `response.output_item.added` / `response.function_call_arguments.*` / `response.completed`. Baut HH2-normalisierte Events.
- **`codex_call(...)`** — `runner/_codex_provider.py:202` — Non-streaming-Wrapper (Codex erfordert stream=true), nimmt `message_stop`-Event.

### Codex-Konverter (`runner/_codex_convert.py`)

- **`_codex_item_id(tool_call_id)`** — `runner/_codex_convert.py:13` — `toolu_…`/`call_…` → `fc_…`.
- **`tools_to_codex(tools)`** — `runner/_codex_convert.py:24` — Anthropic-Tool → Responses-Function (flach).
- **`messages_to_codex(messages, system_prompt)`** — `runner/_codex_convert.py:38` — → (instructions, input_items mit top-level `function_call`/`function_call_output`).
- **`codex_stop_to_anthropic(reason, has_tool_use)`** — `runner/_codex_convert.py:114`

### LiteLLM-Konverter (`runner/_litellm_convert.py`)

- **`tools_to_openai(tools)`** — `runner/_litellm_convert.py:15` — Anthropic → OpenAI-Function-Schema.
- **`messages_to_openai(messages, system_prompt)`** — `runner/_litellm_convert.py:34` — inkl. Image-Block → `image_url` (data-URI), tool_result → `role:tool`-Messages.
- **`openai_response_to_anthropic_blocks(message)`** — `runner/_litellm_convert.py:128` — Rückkonvertierung; generiert `toolu_<uuid>` wenn keine id.
- **`_STOP_MAP` / `openai_stop_to_anthropic(reason)`** — `runner/_litellm_convert.py:161` / `:170` — finish_reason → stop_reason.

### Token-Usage (`runner/_token_usage.py`) — SSOT Stream + Non-Stream

- **`empty_usage()`** — `runner/_token_usage.py:11`
- **`usage_dict(usage)`** — `runner/_token_usage.py:20` — Anthropic-`cache_creation_input_tokens`/`cache_read_input_tokens` → kürzere Keys.
- **`usage_from_litellm(resp)`** — `runner/_token_usage.py:37` — `prompt_tokens`/`completion_tokens` → input/output.

### Events (`runner/events.py`) — SSE-Eventtypen

- **`CompactionStart`** (`compaction_start`) — `runner/events.py:7`
- **`IterationStart`** (`iteration_start`, Feld `iteration`) — `runner/events.py:13`
- **`MessageStart`** (`message_start`) — `runner/events.py:20`
- **`TextDelta`** (`text_delta`, Feld `text`) — `runner/events.py:26` — Streaming-Chunk.
- **`TextBlock`** (`text`, Feld `text`) — `runner/events.py:33` — Non-Streaming konsolidiert.
- **`ToolUseStart`** (`tool_use_start`: call_id/tool_name/arguments) — `runner/events.py:40`
- **`ToolConfirmRequired`** (`tool_confirm_required`) — `runner/events.py:49`
- **`ToolUseResult`** (`tool_use_result`: success/output/error/duration_ms) — `runner/events.py:58`
- **`Done`** (`done`: message_id/iterations/4 Token-Felder) — `runner/events.py:70`
- **`Error`** (`error`: message/fatal/metadata) — `runner/events.py:82`
- **`Event` Union** — `runner/events.py:91`

### Dispatcher — Tool-Ausführung (`runner/dispatcher.py`)

- **`_ERROR_TYPE_PREFIXES` / `_extract_error_type(error)`** — `runner/dispatcher.py:17` / `:20` — „Tool-Crash: ValueError: …" → „ValueError".
- **`execute_tool(tool_use, allowed_tools, ctx, parent_message_id, *, iteration)`** — `runner/dispatcher.py:32` — Persistiert `tools_db.create`, Routing: not-allowed → fail / MCP-Prefix → mcp_bridge.call / Plugin-Prefix → plugin_bridge.call / nicht in REGISTRY → fail / sonst lokales Tool. Fängt ALLE Exceptions → `ToolResult.fail`. `redaction.scrub_result` schwärzt Secrets. `tools_db.finish`.
- **`to_tool_result_block(...)`** — `runner/dispatcher.py:110` — Baut `tool_result`-Block; Truncation auf `max_chars` (+ `mark_truncated`); hängt `media` (URL- oder Datei-basiert) + `tool_name` an.

### Tool-Confirmation (`runner/tool_confirmation.py`)

- **`DEFAULT_TIMEOUT = 300.0`** — `runner/tool_confirmation.py:15` — 5 Min, danach auto-deny.
- **`Decision = Literal["approve","deny"]`** — `runner/tool_confirmation.py:17`
- **`_pending` (dict)** — `runner/tool_confirmation.py:20` — in-memory Future-Store.
- **`register(call_id)`** — `:23` · **`resolve(call_id, decision)`** — `:29` · **`wait(call_id, timeout)`** — `:37` · **`cancel(call_id)`** — `:49`.

### Concurrency-Guard (`runner/concurrency.py`)

- **`SessionAlreadyRunning(RuntimeError)`** — `runner/concurrency.py:29`
- **`_active` (set) / `_lock`** — `runner/concurrency.py:36`
- **`session_run_guard(session_id)` (asynccontextmanager)** — `runner/concurrency.py:41` — Acquire-or-fail.
- **`is_running` / `active_count` / `force_release`** — `runner/concurrency.py:56` / `:61` / `:65`.

### Media-Extraktion (`runner/_media.py`)

- **`IMG_EXT/AUD_EXT/VID_EXT`** — `runner/_media.py:20` · **`ABS_PATH_RE`** — `:27`
- **`_kind` / `_resolve` / `_walk_strings` / `_candidates_from_output`** — `:35`/`:46`/`:59`/`:71`
- **`extract_media(result, workspace)`** — `runner/_media.py:99` — Deterministisch (KEIN LLM) Media-Pfade aus Tool-Output ziehen, Serve-Whitelist prüfen (`settings.servable_prefixes`).

### AgentLink-Handoff-Empfänger (`runner/handoff_receiver.py`)

- **`handle(event)`** — `runner/handoff_receiver.py:26` — Eingehender Handoff: State laden, Ziel-Agent bestimmen, Session erstellen, Runner als Background-Task starten.
- **`_find_target_agent(to_agent_id)`** — `:82` — NUR explizit adressierter aktiver Agent, KEIN Master-Fallback (Issue #177).
- **`_warn_if_unconfirmed(target)`** — `:98` · **`_build_user_input(state)`** — `:110` · **`_run_and_reply(...)`** — `:126` (nutzt `session_run_guard`) · **`_post_reply` / `_post_error_reply`** — `:157` / `:180`.

### Agents — CRUD + Config (`agents/`)

- **`config.create(...)`** — `agents/config.py:21` — Validierung + Config-JSON + Prompt + Workspace.
- **`config.update(agent_id, **changes)`** — `agents/config.py:78` — Protected-Felder (`id/type/created_at/created_by`) entfernt; feld-spezifische Validierung; `normalize_compact_changes`.
- **`config.get_system_prompt` / `set_system_prompt`** — `agents/config.py:107` / `:114`.
- **`config.delete(agent_id)`** — `agents/config.py:123` — `shutil.rmtree`.
- **`_config_utils.save_atomic / normalize / list_all / list_by_owner / get`** — `agents/_config_utils.py:25`/`:32`/`:57`/`:71`/`:75`.
- **`_defaults._BASE_TOOLS`** — `agents/_defaults.py:6` — Default-Tools je Typ (master/project/specialist).
- **`_defaults._LazyDefaultTools` / `DEFAULT_TOOLS`** — `agents/_defaults.py:39` / `:58` — filtert nicht-registrierte Tools (`ask_agent` wenn kein AgentLink) bei jedem Zugriff frisch.
- **Defaults-Konstanten** — `agents/_defaults.py:60-104` (siehe Datenmodell).
- **`_prompt.load_soul / get_soul_components / save_soul_component`** — `agents/_prompt.py:10`/`:23`/`:31`.
- **`_prompt.DEFAULT_PROMPTS`** — `agents/_prompt.py:42` — Typ-Default-Prompts (master/project/specialist).
- **`_prompt.load / save / init_default`** — `agents/_prompt.py:69`/`:79`/`:88` — Soul gewinnt vor system_prompt.md gewinnt vor Default.
- **`_paths.workspace_for / ensure_workspace`** — `agents/_paths.py:8` / `:26` — leitet Workspace-Pfad ab (master/projects/specialists). HydraHive ownt Pfad, kein Free-Form vom User.
- **`_paths.system_prompt_path / config_path / agent_dir / soul_dir / soul_file`** — `agents/_paths.py:33-49`.
- **`_validation.*`** — `agents/_validation.py` — `validate_type` (:15), `validate_status` (:22), `validate_tools` (:29), `_available_models` (:45), `validate_model` (:68), `validate_fallback_models` (:80), `validate_temperature` (:89), `validate_max_tokens` (:96), `validate_compact_*` (:103-127), `validate_max_iterations` (:130), `normalize_compact_changes` (:137).
- **`bootstrap.migrate_tools()`** — `agents/bootstrap.py:27` — idempotent, ergänzt fehlende `_BASE_TOOLS` bei jedem Start (nur hinzufügen, nie entfernen).
- **`bootstrap.ensure_master(username, llm_model)`** — `agents/bootstrap.py:60` — erstellt Master falls keiner existiert (temp=1.0, max_tokens=16000).
- **`bootstrap._write_startup(agent)`** — `agents/bootstrap.py:16` — kopiert `_startup_template.md` (Marvin-Onboarding) in den Workspace.
- **`external_instances.create_instance / list_instances / delete_instance / rotate_key`** — `agents/external_instances.py:14`/`:35`/`:66`/`:79` — User+external-Agent+API-Key als Einheit.
- **`_workspace_links.sync_links_for_user / sync_links_for_project`** — `agents/_workspace_links.py:45` / `:82` — Master bekommt Symlinks zu Projekt-Workspaces.
- **`_startup_template.md`** — Marvin-Persona-Onboarding (6 Fragen → write_memory → selbstlöschen via `rm startup.md`).
- **soul_templates/** — 6 Markdown-Templates (master/buddy/specialist × identity/behavior). NUR Vorlagen, werden nicht zur Laufzeit gemerged (siehe Offene Enden).

### Compaction (`compaction/`)

- **`should_compact(messages, model, *, reserve_tokens, max_turns)`** — `compaction/compactor.py:36` — Token-basiert ODER Turn-basiert.
- **`compact_session(...)`** — `compaction/compactor.py:49` — Ein Compaction-Pass mit voller Telemetrie (`snap`-Dict → `compaction_events`).
- **`total_tokens(messages)`** — `compaction/compactor.py:32`.
- **Konstanten** `DEFAULT_RESERVE_TOKENS=16384` (:23), `DEFAULT_KEEP_RECENT_TOKENS=20000` (:24), `DEFAULT_MAX_TURNS_BEFORE_COMPACT=1000` (:29).
- **`tokens.estimate_text / estimate_dense_text / estimate_message_content / estimate_message / context_window_for`** — `compaction/tokens.py:20`/`:24`/`:31`/`:51`/`:58`.
- **`cut_point.CutPoint` / `find_cut_point` / `_is_tool_results_only` / `_split_turn` / `_find_turn_start`** — `compaction/cut_point.py:9`/`:24`/`:56`/`:68`/`:90`.
- **`hooks.CompactionContext` / `CompactionResult` / `CompactionHooks` / `register` / `all_hooks` / `collect_facts`** — `compaction/hooks.py:23`/`:37`/`:52`/`:65`/`:69`/`:73`.
- **`serialize.serialize_for_summary` (+ `_render_*`)** — `compaction/serialize.py:12` — flacher Text (NICHT Chat-Format), tool_result auf `tool_result_limit` (Default 2000) gekürzt, Secrets redacted.
- **`summarize.summarize` / `_compaction_model` / `_single_summarize` / `_merge_summaries`** — `compaction/summarize.py:36`/`:15`/`:93`/`:126` — chunked bei zu großem Input (#81), hierarchisches Merge.
- **`_chunking.split_at_message_boundaries`** — `compaction/_chunking.py:4` — splittet an `[Role]:`-Zeilen.
- **`redact.redact / add_pattern`** — `compaction/redact.py:12` / `:18` — nutzt zentrale `credentials.redaction`-SSOT.
- **`_prompts.SUMMARY_INSTRUCTIONS / MERGE_INSTRUCTIONS`** — `compaction/_prompts.py:1` / `:42` — festes Markdown-Format (Goal/Constraints/Progress/Decisions/Next/Critical + read/modified-files).
- **`_storage.resolve_through_compaction / previous_summary_text / persist_compaction / extract_files`** — `compaction/_storage.py:13`/`:37`/`:43`/`:77`.

### Externe Consumer / Trigger des Runners

- **`api/routes/_session_msg_helpers.py:39` `sse_run_with_guard`** — SSE-Response mit Concurrency-Guard, 409 bei laufendem Run.
- **`api/routes/sessions_messages.py:202`** — Supervisor-Inject (Admin → fremde Session, fire-and-forget Background-Task).
- **`api/routes/sessions.py:97` `POST /{session_id}/tool-confirm/{call_id}`** — ruft `tool_confirmation.resolve`.
- **`communication/_agent_glue.py:156`** — Channel-Agent-Runs (WhatsApp/Mail) mit `extra_system` (Sender-Rahmung).
- **`api/routes/_sse.py` `encode_event / to_sse`** — Serialisiert Events als SSE-Frames.

---

## WIE

### Haupt-Ablauf eines Runs (`run()` in `runner/runner.py`)

1. **Setup** (`runner.py:71-119`):
   - `sessions_db.get` → Error wenn fehlt; `agent_config.get` → Error wenn fehlt/verwaist; Agent muss `status=="active"`.
   - `ensure_workspace(agent)` → `ToolContext` (session_id/agent_id/user_id/workspace/config/project_id).
   - `session_start(...)` (Lifecycle, idempotent).
   - `base_system_prompt = agent_config.get_system_prompt(...)` → `with_emote_hint(... is_buddy=...)`.
   - Tool-Schemas: lokale (`schemas_for`) + MCP (`mcp_bridge.schemas_for_servers`) + Plugin (`plugin_bridge.schemas_for`); `allowed_tools = local + MCP-Namen`.
   - `messages_db.append(session_id,"user",user_input)` — User-Turn persistiert.
   - Per-Agent-Compaction-Params (`compact_model/_tool_result_limit/_reserve_tokens/_threshold_pct/_max_turns`), `tool_result_max_chars`, `cache_ttl`, `max_iterations`, Skills.
2. **Proaktiver Recall** (`runner.py:121-136`) — nur wenn `agent.longterm_memory`:
   - **Recall A**: `top_cards_for(agent_id, limit=8)` (recency × salience) — einmal pro Session, in gecachten Stable-Prompt gewebt.
   - **Recall C**: `search_cards(user_text, limit=3)` NUR wenn Eingabe ≥3 Wörter (kein Token-Brand bei „test"). In volatile Block.
   - Komplett best-effort: Exception → warning, weiter.
3. **Iterations-Loop** `for iteration in range(max_iterations)` (`runner.py:138`):
   - `yield IterationStart(iteration+1)`.
   - **prepare_history** (`runner.py:142`): `list_for_llm` (kept-portion nach letzter Compaction). `effective_reserve` aus `compact_reserve` UND `window*(1-threshold/100)` (max). `should_compact` → ggf. `CompactionStart` + `compact_session(auto)` + reload.
   - **compose_system_prompts** (`runner.py:153`): stable/volatile/summary. Summary aus `get_latest_summary`. Bei `longterm_memory` Side-Effect auf tool_schemas/allowed_tools.
   - **Per-Session-Override** (`runner.py:168`): `sessions_db.get` RE-READ → `metadata.model_override` + `metadata.reasoning_effort`. `primary_model = override or agent.llm_model`. (Re-read damit Chat-Header-Switch ohne Server-Restart greift.)
   - **stream_llm_call** (`runner.py:176`): `to_anthropic_messages(heal_orphan_tool_uses(history))`. Bei Exception: `errors_log.record`, `session_end(abandoned)`, `yield Error`, return.
   - **Token-Akkumulation + Telemetrie** (`runner.py:202-238`): Totals summieren; `llm_calls_db.insert` (provider/model/temp/tokens/cost_micros/turn_in_session) — Insert-Fehler loggt nur, Lauf läuft weiter.
   - **Assistant-Persist** (`runner.py:240`): `messages_db.append(assistant, result.blocks, metadata={...tokens, model, stop_reason, iteration})`; `history.append`.
   - **stop_reason-Auswertung**:
     - `max_tokens` (`runner.py:254`) → `close_open_tool_uses`, `session_end(abandoned)`, `yield Error` (Tool-Args unvollständig), return.
     - **kein tool_use** (`runner.py:264`) → `session_end(completed)`; **fire-and-forget** `_safe_compress` (compress-Pipeline via `asyncio.create_task` + `errors_log.capture`); `yield Done(...)`, return.
   - **Loop-Detection** (`runner.py:284`): Signatur = `name:json(input)` aller tool_uses; letzte 3 (`LOOP_DETECTION_WINDOW`); 3 identische → `close_open_tool_uses`, `session_end(abandoned)`, `yield Error`, return.
   - **process_tool_uses** (`runner.py:296`): siehe unten. Letzter yield = `result_blocks`.
   - `tool_msg = messages_db.append(user, result_blocks)`; `history.append`. Schleife.
4. **Nach max_iterations** (`runner.py:311-333`):
   - **Pre-Resume-Compaction (#143)**: wenn `threshold<100` und `should_compact(reserve=window//2)` → `compact_session(max_iterations_resume, threshold=50)`. Damit „Weitermachen" nicht sofort wieder knallt.
   - `session_end(paused)`; `yield Error(kind="max_iterations", last_assistant_message=...)`.

### Tool-Loop (`process_tool_uses`, `runner/_runner_tools.py:22`)

Pro `tool_use`: `yield ToolUseStart`. Wenn `require_confirm`: `register` + `yield ToolConfirmRequired` + `await wait` → bei `deny` `ToolResult.fail` + `ToolUseResult(success=False)` + Result-Block (KEIN record_observation — User-Ablehnung ist Kontroll-Ereignis), `continue`. Sonst: `execute_tool` → `record_observation` (HOOK_POST_TOOL_USE / _FAILURE) → `yield ToolUseResult` → `to_tool_result_block` (mit max_chars + record_id). Final `yield result_blocks`.

### LLM-Call-Pfad (`call_with_stream_or_fallback`, `runner/_call.py:64`)

- `models = [primary] + fallback_models`.
- **Streaming-Phase** (nur Primärmodell): bis zu 2 Versuche. `stream_with_tools` → mappt `message_start`→`MessageStart`, `text_delta`→`TextDelta` (setzt `text_sent`), `message_stop`→finale Blocks+Tokens (`streamed_ok=True`). `StreamingNotSupported`→break (Fallback). `CodexModelNotAllowed`→raise. Andere Exception: Versuch 1 + kein Text gesendet → 1.5s sleep + retry; sonst break.
- Wenn `streamed_ok`: `yield CallResult(model=primary)`, return.
- **Non-Streaming-Fallback** (`runner/_call.py:137`): iteriere alle `models`. `call_with_tools`. Bei Exception: `should_failover(e) and not is_last` → nächstes Modell, sonst raise. Text als `TextBlock`, dann `CallResult(model=tatsächlich)`. Alle fehlgeschlagen → raise `last_exc`.

### Provider-Routing (`call_with_tools`, `runner/llm_bridge.py:13`)

`_load_config` → target. MiniMax → minimax. `claude-*` → Anthropic (OAuth via `resolve_anthropic_token` — refresht automatisch). `openai-codex/` → Codex (OAuth via `resolve_openai_codex_token`). Rest → `apply_keys` + LiteLLM (System = system+summary+volatile gejoined).

### Anthropic-System-Block-Reihenfolge (`build_anthropic_kwargs`, `runner/_anthropic_payload.py:83`)

OAuth-Client (auth_token + OAuth-Headers) oder Plain-Client. system_blocks: **(1)** OAuth-Identity (nur OAuth) **(2)** system_prompt MIT cache_control **(3)** summary_system MIT cache_control **(4)** volatile_system OHNE cache_control (sonst bricht Cache täglich). messages → `with_cache_breakpoint` (letzte Message). tools → cache_control nur am letzten Tool. `apply_effort(kwargs, model, reasoning_effort)`.

### Reasoning-Effort (`apply_effort`, `llm/_anthropic.py:45`)

- **Neuer Pfad** (Claude 4.6+: opus-4-6/4-7/4-8, sonnet-4-6): `thinking={"type":"adaptive"}` + `output_config.effort` ∈ {low,medium,high,xhigh,max}.
- **Legacy-Pfad** (Claude 4.5/älter, MiniMax): `thinking={"type":"enabled","budget_tokens":...}` (low=1024/medium=4096/high=16384), `temperature=1.0`, max_tokens hochziehen.
- `effort=None`/unbekannt → no-op.

### Compaction-Pass (`compact_session`, `compaction/compactor.py:49`)

`list_for_session` (voll) → `resolve_through_compaction` (visible = letzte compaction-Summary + kept tail). `<4 visible` → skip(too_short). `find_cut_point(visible, keep_recent_tokens=20000)`: rückwärts Tokens akkumulieren bis `keep_recent_tokens` überschritten, niemals an tool_result schneiden, Einzel-Riesenturn → `_split_turn` an Assistant-Message. `kept<=0 && !split` → skip(nothing_to_compact). `to_summarize=[:cut]`, `kept=[cut:]`. Hooks-Pipeline: `before_compact` (cancel/custom-summary), `pre_compact_flush`, `collect_facts`, `custom_summarize`, sonst Default-`summarize` (chunked+merge). `extract_files` (file_read→readFiles, file_write/patch→modifiedFiles). `persist_compaction` (role="compaction", `metadata.firstKeptEntryId`). `after_compact`. Telemetrie-`snap` immer in `finally._emit()`.

### History-Resolution (`list_for_llm`, `db/_messages_llm.py:10`)

Findet letzte `role='compaction'`-Message; ohne → ganze History; mit `firstKeptEntryId` → `id >= first_kept` (UUID v7 sortiert chronologisch, vermeidet equal-created_at-Kollision). Liefert NUR kept-portion; Summary separat via `get_latest_summary`.

### History-Heilung (`heal_orphan_tool_uses`, `runner/context.py:8`)

Pro Assistant-Message mit tool_uses: prüfe nächste User-Message auf passende tool_results; fehlende → synthetische is_error-tool_results in nächste Message ODER neue synthetic Message. Dann `_strip_orphan_tool_results` + `_deduplicate_tool_results`. Immer nach `list_for_llm` und vor `to_anthropic_messages` aufgerufen (`runner.py:181`).

### SSE-Datenfluss (Klick → Antwort)

Browser POST /sessions/{id}/messages → `sse_run_with_guard` → `is_running`-Check (409) → `session_run_guard` → `runner_run(...)` → `to_sse(events)` → pro Event `encode_event` (`event: <type>\ndata: <json>\n\n`) → Browser. Tool-Confirm: Frontend bekommt `tool_confirm_required` → POST /tool-confirm/{call_id} → `tool_confirmation.resolve` löst Future → Runner fährt fort.

---

## WO (Datei:Zeile — Sammelreferenz)

### runner/
- `runner/runner.py:64` `run()` · `:45` MAX_ITERATIONS · `:46` LOOP_DETECTION_WINDOW · `:49` `_user_text` · `:121-136` Recall A/C · `:138` Iter-Loop · `:142` prepare_history · `:153` compose · `:168` Session-Override-Reread · `:176` stream_llm_call · `:210` llm_calls-Insert · `:254` max_tokens-Branch · `:264` Done-Branch+compress · `:284` Loop-Detection · `:296` process_tool_uses · `:311` Pre-Resume-Compaction · `:330` paused.
- `runner/_runner_iter.py:17` IterationResult · `:28` prepare_history · `:72` stream_llm_call.
- `runner/_runner_tools.py:22` process_tool_uses.
- `runner/_runner_helpers.py:7` close_open_tool_uses.
- `runner/_call.py:31` CallResult · `:52` _sanitize_blocks · `:64` call_with_stream_or_fallback · `:95` Streaming-Retry-Loop · `:137` Non-Streaming-Failover.
- `runner/_failover.py:11` _FAILOVER_PATTERNS · `:25` should_failover.
- `runner/system_prompt.py:18` compose · `:54` _stable_section · `:82` _volatile_section · `:105` _inject_longterm_memory · `:131` render_cards_block · `:152` render_search_block.
- `runner/_emote_hint.py:13` EMOTE_NAMES · `:35` HYDRA_EMOTE_HINT · `:46` with_emote_hint.
- `runner/context.py:8` heal_orphan_tool_uses · `:68` _deduplicate · `:94` _strip_orphan · `:130` to_anthropic_messages · `:155` _ANTHROPIC_ALLOWED · `:168` _BLOCKS_TO_STRIP · `:203` extract_tool_uses.
- `runner/llm_bridge.py:13` call_with_tools.
- `runner/llm_bridge_stream.py:17` StreamingNotSupported · `:21` stream_with_tools.
- `runner/_llm_bridge_backends.py:23` anthropic_call · `:63` minimax_anthropic_call · `:107` _is_tool_use_unsupported · `:122` litellm_call.
- `runner/_anthropic_payload.py:16` cache_control · `:23` with_cache_breakpoint · `:56` block_to_dict · `:69` strip_minimax_cache_control · `:83` build_anthropic_kwargs · `:137` build_minimax_kwargs.
- `runner/_stream_providers.py:15` _map_event · `:43` anthropic_stream · `:95` minimax_stream.
- `runner/_codex_provider.py:22` CODEX_URL · `:26` CodexModelNotAllowed · `:79` codex_stream · `:202` codex_call.
- `runner/_codex_convert.py:13` _codex_item_id · `:24` tools_to_codex · `:38` messages_to_codex · `:114` codex_stop_to_anthropic.
- `runner/_litellm_convert.py:15` tools_to_openai · `:34` messages_to_openai · `:128` openai_response_to_anthropic_blocks · `:170` openai_stop_to_anthropic.
- `runner/_token_usage.py:11` empty_usage · `:20` usage_dict · `:37` usage_from_litellm.
- `runner/events.py:7-91` Event-Klassen.
- `runner/dispatcher.py:20` _extract_error_type · `:32` execute_tool · `:110` to_tool_result_block.
- `runner/tool_confirmation.py:15` DEFAULT_TIMEOUT · `:23-49` register/resolve/wait/cancel.
- `runner/concurrency.py:29` SessionAlreadyRunning · `:41` session_run_guard · `:56-65` is_running/active_count/force_release.
- `runner/_media.py:27` ABS_PATH_RE · `:99` extract_media.
- `runner/handoff_receiver.py:26` handle · `:82` _find_target_agent · `:126` _run_and_reply.

### agents/
- `agents/config.py:21` create · `:78` update · `:107/:114` get/set_system_prompt · `:123` delete.
- `agents/_config_utils.py:25` save_atomic · `:32` normalize · `:57/:71/:75` list_all/list_by_owner/get.
- `agents/_defaults.py:6` _BASE_TOOLS · `:39` _LazyDefaultTools · `:60-104` Default-Konstanten.
- `agents/_prompt.py:10` load_soul · `:42` DEFAULT_PROMPTS · `:69` load · `:88` init_default.
- `agents/_paths.py:8` workspace_for · `:26` ensure_workspace.
- `agents/_validation.py:45` _available_models · `:68` validate_model · `:137` normalize_compact_changes.
- `agents/bootstrap.py:27` migrate_tools · `:60` ensure_master.
- `agents/external_instances.py:14` create_instance · `:66` delete_instance · `:79` rotate_key.
- `agents/_workspace_links.py:45` sync_links_for_user · `:82` sync_links_for_project.

### compaction/
- `compaction/compactor.py:36` should_compact · `:49` compact_session · `:104` _emit.
- `compaction/tokens.py:20` estimate_text · `:24` estimate_dense_text · `:58` context_window_for.
- `compaction/cut_point.py:24` find_cut_point · `:68` _split_turn.
- `compaction/hooks.py:65` register · `:73` collect_facts.
- `compaction/serialize.py:12` serialize_for_summary.
- `compaction/summarize.py:15` _compaction_model · `:36` summarize · `:126` _merge_summaries.
- `compaction/_chunking.py:4` split_at_message_boundaries.
- `compaction/redact.py:12` redact.
- `compaction/_prompts.py:1` SUMMARY_INSTRUCTIONS · `:42` MERGE_INSTRUCTIONS.
- `compaction/_storage.py:13` resolve_through_compaction · `:43` persist_compaction · `:77` extract_files.

### Externe Verdrahtung
- `db/_messages_llm.py:10` list_for_llm · `db/messages.py:13` append · `:72` get_latest_summary.
- `api/routes/_session_msg_helpers.py:39` sse_run_with_guard · `api/routes/_sse.py` encode_event/to_sse.
- `api/routes/sessions.py:97` tool-confirm-Route · `api/routes/sessions_messages.py:202` inject.
- `communication/_agent_glue.py:156` Channel-Run mit extra_system.
- `llm/_anthropic.py:45` apply_effort · `:25` EFFORT_LEVELS · `:34` EFFORT_TO_BUDGET · `:19` _OAUTH_IDENTITY · `:13` _OAUTH_HEADERS.
- `tools/_sessions.py:56` session_start · `:90` session_end (Status active/completed/abandoned/paused).
- `tools/_compress.py` compress_session (fire-and-forget am Session-Ende).

---

## WARUM (nicht-offensichtliche Verdrahtung, Invarianten, Gotchas)

### Stable vs. Volatile System-Prompt — Cache-Invariante
Anthropic prüft den GANZEN System-Block byteweise für Prompt-Caching (nicht nur den cache_control-Bereich). Würde die Uhrzeit im Prompt stehen, bräche der Cache jede Minute. Deshalb enthält `_volatile_section` NUR das Datum → Cache bricht max. einmal pro Tag (Issue #141). volatile_system steht OHNE cache_control GANZ HINTEN — würde es davor stehen oder cache_control tragen, wäre der gecachte stable-Teil täglich invalidiert. **Wenn man die System-Block-Reihenfolge in `build_anthropic_kwargs` anfasst, bricht der Cache.**

### Recall A in stable, Recall C in volatile — bewusst getrennt
Recall A (`render_cards_block`) hängt an den gecachten Stable-Prompt → ändert sich nur bei nächtlicher Konsolidierung, cache-stabil innerhalb der Session. Recall C (`render_search_block`) ist cue-getriggert (zur aktuellen Eingabe) und MUSS deshalb in den volatile Block — sonst würde jeder neue Cue den Cache brechen. Recall C feuert nur bei ≥3 Wörtern, damit „test"/Einzelwörter keinen Token-Brand und keine Cache-Invalidierung auslösen.

### `longterm_memory` mutiert tool_schemas/allowed_tools IN-PLACE
`compose()` → `_inject_longterm_memory` hängt Datamining-Tools an die ÜBERGEBENEN Listen an (kein Copy). Da `compose` in JEDER Iteration läuft, schützt das `if tool.name not in existing`-Guard vor Duplikaten. Ändert man das zu Copy-Semantik, fehlen die Tools im Call; lässt man den Guard weg, wachsen die Listen pro Iteration.

### Modell-Override Re-Read pro Iteration
`sessions_db.get` wird in JEDER Iteration neu gelesen (`runner.py:168`), nicht einmal gecacht — damit ein Chat-Header-Modell-Switch ODER reasoning_effort-Wechsel MITTEN in einem laufenden Multi-Iter-Run greift, ohne Server-Restart. Caching dieser Werte würde den Live-Switch brechen.

### Streaming nur am Primärmodell, Failover nur Non-Streaming
Mid-Stream-Fehler lassen sich nicht zurückrollen (User hat schon Tokens gesehen). Deshalb: Streaming-Retry nur solange `text_sent==False`; sobald Text floss, kein Retry mehr (sonst Doppel-Text). Failover über mehrere Modelle passiert ausschließlich im Non-Streaming-Pfad. `CodexModelNotAllowed` wird explizit durchgereicht (nicht failover-würdig — der Account hat das Modell schlicht nicht).

### `close_open_tool_uses` / `heal_orphan_tool_uses` — Session-Vergiftungs-Schutz
Anthropic verlangt: jedes `tool_use` MUSS im nächsten User-Turn ein passendes `tool_result` haben. Bricht ein Turn vorher ab (max_tokens, Loop, LLM-Fehler), bleiben „offene" tool_uses → JEDER nächste Send gibt 400. `close_open_tool_uses` schreibt synthetische is_error-Results in die DB; `heal_orphan_tool_uses` heilt zusätzlich zur Call-Zeit (ohne DB-Mutation) und strippt/dedupliziert. **Entfernt man eine dieser Funktionen, vergiften abgebrochene Turns die Session dauerhaft.**

### thinking-Blöcke werden IMMER gestrippt (Issue #79)
`_BLOCKS_TO_STRIP={"thinking"}` in `context.py`: Thinking-Blöcke tragen eine Signatur. Schickt man sie zurück ohne Extended-Thinking im aktuellen Call zu aktivieren → „Invalid signature in thinking block" 400. HH2 nutzt Extended-Thinking nicht aktiv im Re-Send → komplett strippen. (Im _stream_providers wird `thinking_delta` ebenfalls verworfen.)

### `id >= first_kept` statt `created_at >= ...` (UUID v7)
`list_for_llm` nutzt UUID-v7-IDs (chronologisch sortierbar) statt created_at, weil zwei Messages denselben created_at-Timestamp haben können → sonst würde die falsche Message in die kept-portion rutschen und einen orphan tool_result erzeugen (genau der Edge-Case den `_strip_orphan_tool_results` als zweites Sicherheitsnetz abfängt).

### Cache-TTL Default = "5m", NICHT "1h"
`DEFAULT_CACHE_TTL="5m"` (`_defaults.py:88`). Längere TTL verdoppelt die Write-Kosten beim Initial-Write, aber server-side Eviction passiert trotzdem <5min — „1h" hat die Kosten verdoppelt ohne Nutzen. Quelle dokumentiert: claude-code-source-code/.../state.ts:251.

### max_iterations=16 statt 30 (Token-Audit #129/#125)
30 triggerte keinen Abbruch sondern User-Restarts (49-Call-Repo-Review-Pattern). 16 zwingt fokussiertes Vorgehen, spart 30-50% Tokens. Komplexe Reviews erhöhen per-Agent. **Senkt man unter den Wert, brechen lange legitime Tasks ab; erhöht man ihn, kommt das Token-Verschwendungs-Pattern zurück.**

### compact_threshold_pct=75 + Pre-Resume-Compaction
Auto-Compact bei 75% Fülle (statt 100%) spart ~20-30% pro Turn. Die Pre-Resume-Compaction nach max_iterations (Reserve=window//2 ⇒ Trigger >50%) verhindert, dass ein „Weitermachen"-Klick sofort wieder nach 16 Iter knallt. **Bei threshold_pct=100 ist die Pre-Resume-Compaction deaktiviert (`if compact_threshold_pct < 100`).**

### MiniMax-Sonderbehandlung an drei Stellen
(1) `strip_minimax_cache_control` — cache_control → HTTP 500. (2) System als EIN String statt Block-Array (Array bricht nach Compaction). (3) `_compaction_model` weicht für Compaction auf non-MiniMax aus (MiniMax aktiviert intern Web-Search → 500). **Diese drei sind unabhängig; einen wegzulassen bringt MiniMax-500er zurück.**

### Concurrency-Guard ist in-memory & Single-Process
`_active`-Set lebt im Prozess. Funktioniert NUR mit einem Uvicorn-Worker. Bei mehreren Workern müsste auf DB-Status (`sessions.status='running'`) umgestellt werden. Symptom ohne Guard: doppelte Iterationen (turn_in_session=1 zweimal), parallele Tool-Aufrufe, ~46.5¢ verschenkt im konkret beobachteten Fall (#129).

### AgentLink-Handoff: KEIN Master-Fallback (Issue #177)
`_find_target_agent` liefert NUR den explizit adressierten aktiven Agenten — niemals den unrestricted Admin-Master. Ein externer Handoff darf nie auf den Master eskalieren. Unadressierte/unbekannte/inaktive Handoffs werden abgelehnt (`_post_error_reply`). Interne Handoffs kodieren die Ziel-ID im reason-Präfix `hh-target:<uuid>|...` (weil `extra{}` von post_state nicht gesendet wird).

### Soul gewinnt vor system_prompt.md vor Default
`_prompt.load`: erst `load_soul` (merged soul/*.md alphabetisch), dann `system_prompt.md`, dann typ-spezifischer `DEFAULT_PROMPTS`. Atomare Writes (temp+rename) verhindern halb-geschriebene Dateien bei parallelen Reads.

### Secret-Redaction an zwei Engstellen, EINE SSOT
`dispatcher.execute_tool` ruft `redaction.scrub_result` BEVOR der Output in tools_db UND ins Transcript/Stream geht. `compaction.redact` nutzt dieselbe `credentials.redaction`-SSOT. Zwei divergierende Listen waren die Ursache des OpenRouter-Key-Leaks (Drift) — neue Patterns NUR an einer Stelle pflegen.

### Emote-Hint nur zur Laufzeit, nur für Buddy
`with_emote_hint` hängt die Emote-Liste an, OHNE sie in den editierbaren Prompt zu backen. `EMOTE_NAMES` spiegelt manuell `frontend/.../hydraEmotes.ts` — bei Frontend-Änderung hier nachziehen (es gibt keine automatische Synchronisation).

### compress vs. compact — zwei verschiedene Pipelines
`compact_session` (compaction/) = Context-Window-Verdichtung (Summary in History). `compress_session` (tools/_compress.py) = Observation-Pipeline (RawObservation→CompressedObservation fürs Langzeitgedächtnis/Mirror-Cards). Letztere läuft fire-and-forget am Session-Ende und speist Recall A/C. Namen sind verwechselbar — sie haben NICHTS miteinander zu tun.

### Token-Telemetrie ist best-effort, blockiert nie
`llm_calls_db.insert`, `compaction_events.insert`, `mark_truncated` sind alle in try/except — Telemetrie-Verlust loggt nur, der Lauf läuft weiter. Invariante: Telemetrie darf NIE einen User-Turn killen.

---

## Datenmodell

### Agent-Config (JSON, `agents/<id>/config.json`)
Felder (gesetzt in `create`, backfilled in `normalize`): `id`, `type` (master/project/specialist), `name`, `owner`, `created_by`, `llm_model`, `fallback_models[]`, `tools[]`, `mcp_servers[]`, `description`, `temperature`, `max_tokens`, `thinking_budget`, `status` (active/disabled), `created_at`, `updated_at`, `external` (bool), optional `project_id`, `domain`, `system_prompt`.
Runner-/Compaction-relevante (normalize-backfilled): `disabled_skills[]`, `require_tool_confirm` (bool), `is_buddy` (bool), `compact_model` (""=llm_model), `compact_tool_result_limit`, `compact_reserve_tokens`, `compact_threshold_pct`, `compact_max_turns` (optional, kein Default), `max_iterations`, `tool_result_max_chars`, `cache_ttl`, `longterm_memory` (bool, NICHT in normalize — nur gelesen).

### Default-Konstanten (`agents/_defaults.py`)
- `DEFAULT_TEMPERATURE = 0.7` (:60)
- `DEFAULT_MAX_TOKENS = 16384` (:65) — 8192 war zu knapp (#142, 20% Kosten an max_tokens-Restarts).
- `DEFAULT_THINKING_BUDGET = 0` (:66)
- `DEFAULT_COMPACT_MODEL = ""` (:71)
- `DEFAULT_COMPACT_TOOL_RESULT_LIMIT = 2000` (:75)
- `DEFAULT_TOOL_RESULT_MAX_CHARS = 12_000` (:79) — Live-Truncation, 0=aus.
- `DEFAULT_CACHE_TTL = "5m"` (:88)
- `DEFAULT_COMPACT_RESERVE_TOKENS = 16_384` (:91)
- `DEFAULT_COMPACT_THRESHOLD_PCT = 75` (:95)
- `DEFAULT_MAX_ITERATIONS = 16` (:104)

### Compaction-Defaults (`compaction/compactor.py`)
- `DEFAULT_RESERVE_TOKENS = 16_384` (:23)
- `DEFAULT_KEEP_RECENT_TOKENS = 20_000` (:24)
- `DEFAULT_MAX_TURNS_BEFORE_COMPACT = 1000` (:29) — 24 verursachte Endlos-Compaction-Loops.
- Token-Schätzung: `_CHARS_PER_TOKEN = 3.5` (tokens.py:10), `_CHARS_PER_TOKEN_DENSE = 1.2` (:17, für serialisierte Dumps), `_USABLE_FRACTION = 0.80` (summarize.py:12).
- `DEFAULT_TOOL_RESULT_LIMIT = 2000` (serialize.py:9).

### Effort/Thinking (`llm/_anthropic.py`)
- `EFFORT_LEVELS = (low, medium, high, xhigh, max)` (:25)
- `EFFORT_PARAM_MODELS = (opus-4-6, opus-4-7, opus-4-8, sonnet-4-6)` (:31)
- `EFFORT_TO_BUDGET = {low:1024, medium:4096, high:16384}` (:35)
- `MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"` (:23)
- `_OAUTH_HEADERS` (anthropic-beta claude-code/oauth/fine-grained-tool-streaming/prompt-caching, user-agent claude-cli/2.1.62) (:13), `_OAUTH_IDENTITY` („You are Claude Code…") (:19).

### context_window_for (`compaction/tokens.py:58`) — Window-Tabelle
opus-4-8/4-7 → 1_000_000; sonnet-4/opus-4/haiku-4/claude-3-7/3-5 → 200_000; gpt-4(o) → 128_000; gemini → 1_000_000; minimax → 256_000; deepseek/llama/mistral/mixtral → 128_000; qwen2.5(-coder) → 32_000; qwen3* → 262_144; default → 32_000.

### Tabellen / DB
- **`messages`** — Rollen `user`/`assistant`/`tool`(legacy)/`system`/`compaction`. `compaction`-Row: content=Summary, `metadata.firstKeptEntryId`, `tokensBefore`, `isSplitTurn`, `source`, `readFiles[]`, `modifiedFiles[]`, `facts`. Assistant-metadata: input/output/cache_creation/cache_read_tokens, model, stop_reason, iteration. (db/messages.py, _messages_llm.py)
- **`llm_calls`** (#129 Token-Audit) — pro LLM-Call: session_id, agent_id, user_id, provider, model, temperature, max_tokens, reasoning_effort, prompt/completion/cache_read/cache_creation_tokens, stop_reason, ttft_ms (None), total_ms, cost_micros, turn_in_session. (runner.py:212)
- **`compaction_events`** — `snap`-Felder (agent_id, user_id, model, triggered_by, trigger_threshold_pct, skipped, skip_reason, messages_*, tokens_before/after_estimate, cut_*, summary_chars, facts_count, files_extracted_count, compaction_message_id, error, duration_ms). (compactor.py:74)
- **`tool_calls`** — via `tools_db.create/finish/mark_truncated` (parent_message_id, tool_name, args, session_id, agent_id, user_id, tool_use_id, iteration, result, status, duration_ms, error_type, error_message). (dispatcher.py)
- **`agent_handoffs`** — incoming_state_id, from_agent, agent_id, session_id, status. (handoff_receiver.py)
- **Session-Files** (`agents/<id>/sessions/<sid>.json`) — id, agent_id, project, started_at, ended_at, status (active/completed/abandoned/paused), observation_count, model, first_prompt[:500], summary. (tools/_sessions.py)

### Session-Metadata-Keys (Live-Override, gelesen in runner.py:168)
- `metadata.model_override` — Chat-Header-Modell-Switch.
- `metadata.reasoning_effort` — Effort-Switch.

### `triggered_by`-Werte (Compaction-Telemetrie)
`auto` (Runner pre-iteration), `max_iterations_resume` (Runner nach max_iterations), `manual` (API).

### Env-Vars / externe Auth (indirekt)
OAuth-Tokens via `resolve_anthropic_token` (sk-ant-oat…) und `resolve_openai_codex_token` (access/account_id). MiniMax-Key aus llm.json (`_get_minimax_key`). Provider-Keys via `apply_keys(cfg)` → ENV für LiteLLM. `settings.servable_prefixes` (Media-Whitelist), `settings.agentlink_agent_id`, `settings.agents_dir`, `settings.data_dir`.

### Recall-Card-Felder (gelesen in system_prompt.py)
`gist`, `topics[]`, `valence` (Recall A); `gist`, `source.session_id` (Recall C). Quelle: `db/_mirror_cards.top_cards_for(agent_id, limit=8)` + `search_cards(query, limit=3)`.

---

## Offene Enden (TODOs, tote/halbfertige Teile, Drift, Aufräum-Kandidaten)

1. **soul_templates/ werden nicht genutzt** — `agents/soul_templates/*.md` (6 Dateien: master/buddy/specialist × identity/behavior) sind reine Vorlagen. `_prompt.load_soul` liest aus `agents/<id>/soul/*.md`, NICHT aus `soul_templates/`. Kein Code kopiert die Templates in einen Agent. `buddy_*`-Templates existieren, aber `create()` legt nie ein `soul/`-Verzeichnis an (nur `init_default` → flaches `system_prompt.md`). Die Soul-Komponente `background` ist in `SOUL_COMPONENTS` (_prompt.py:7) gelistet, aber es gibt kein `background`-Template. **Toter/halbfertiger Pfad — entweder verdrahten oder entfernen.**

2. **`_context_injection.cpython-312.pyc` ohne Quelle** — In `agents/__pycache__/` liegt `_context_injection.cpython-312.pyc`, aber KEINE `_context_injection.py`. Verwaiste Compile-Artefakt einer gelöschten Datei (auch `_config.pyc` referenziert). Aufräum-Kandidat (`find -name '*.pyc'` clean).

3. **`thinking_budget` faktisch tot** — Agent-Config trägt `thinking_budget` (create/normalize), aber der Runner liest es NIE. Effort läuft ausschließlich über `reasoning_effort` (Session-Metadata) → `apply_effort`. `thinking_budget` ist ein verwaister Config-Key. Default ist überall 0.

4. **`compact_max_turns` ohne Default** — Wird in `run()` gelesen (`agent.get("compact_max_turns")`), aber `normalize` backfilled es NICHT (anders als alle anderen compact_*). Bei alten Configs immer None → `should_compact` nutzt dann `DEFAULT_MAX_TURNS_BEFORE_COMPACT=1000`. Inkonsistenz zum Normalize-Muster.

5. **`thinking`-Block-Rendering in serialize, aber Strip in context** — `serialize.py:87` rendert `[Assistant thinking]:` für die Compaction-Summary, während `context.py:168` thinking komplett strippt. Inkonsistent (Compaction sieht Thinking-Inhalt, der Re-Send nicht) — vermutlich Absicht (Summary darf Thinking-Kontext nutzen), aber nirgends dokumentiert.

6. **`ttft_ms=None` hartcodiert** — `runner.py:226` schreibt `ttft_ms=None` in jeden llm_call. Time-to-first-token wird trotz Streaming nicht gemessen — Telemetrie-Lücke. (Der Stream sieht das erste `text_delta`, aber misst keinen Timestamp.)

7. **`normalize` wird importiert aber kaum genutzt** — `_config_utils.normalize` ist in `agents/config.py:10` importiert, dort aber nie direkt aufgerufen (nur via `get`/`list_all`). Toter Import in config.py.

8. **`fut` Zwischenvariable ohne Zweck** — `_runner_tools.py:43` `fut = tool_confirmation.register(tu_id)` … `_ = fut`. Der Future wird registriert aber das Handle nie benutzt (wait holt ihn aus `_pending`). Der `_ = fut` ist ein expliziter „unused"-Marker. Leichte Code-Smell-Redundanz.

9. **`add_pattern`-Label-Drift** — `compaction/redact.py:18` `add_pattern(pattern, replacement="")` — der `replacement`-Parameter wird ignoriert (zentrale Redaction nutzt einheitlichen Platzhalter). Signatur trägt totes Argument für Backwards-Compat.

10. **LiteLLM-Pfad kann Cache-Tokens nicht zählen** — `usage_from_litellm` liest `cache_creation_input_tokens`/`cache_read_input_tokens`, die OpenAI-kompatible Provider praktisch nie liefern → für alle Nicht-Anthropic-Modelle sind cache-Spalten in `llm_calls` strukturell 0. Cost-Berechnung für diese Provider ignoriert Caching.

11. **`extract_files` nur über `args.path`** — `_storage.extract_files` erkennt gelesene/geänderte Dateien nur an einem `path`-Argument von file_read/file_write/file_patch. shell_exec-`cat`/`>`-Operationen oder Tools mit anderem Param-Namen werden NICHT erfasst → unvollständige readFiles/modifiedFiles in der Summary. (`_FILE_PATH_RE` in _storage.py:74 ist definiert, wird aber in extract_files gar nicht verwendet — toter Regex.)

12. **`merge_text_blocks` ungenutzt im Runner** — `context.py:197` exportiert `merge_text_blocks`, aber der Runner-Loop nutzt es nicht (Text fließt über Events). Vermutlich nur für externe Caller/Logging — Verdrahtung prüfen.

13. **`CompactionStart`-Event ohne Frontend-Sichtbarkeit?** — Wird in `prepare_history` geyieldet und über SSE serialisiert, aber laut MEMORY.md wurde „SSE-Progress" teils entfernt. Ob das Frontend `compaction_start` noch rendert, ist aus dem Backend nicht verifizierbar — Cross-Check Frontend nötig.

14. **`_codex_convert.tools_to_codex` setzt `strict: None`** — `_codex_convert.py:34` — `strict: None` statt weglassen; harmlos, aber unsauber gegenüber der Responses-API-Spec (erwartet bool/absent).

15. **Doppelte `logging`-Imports** — `_llm_bridge_backends.py:145` re-importiert `logging` lokal in `litellm_call`, obwohl Modul-Level (`:4`) bereits einen Logger hat. Redundanz.
