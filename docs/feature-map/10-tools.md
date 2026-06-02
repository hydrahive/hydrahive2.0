# Agent-Tools

> Subsystem-Wurzel: `core/src/hydrahive/tools/`
> Stand der Quelle: gelesen am 2026-06-02, alle 47 `.py`-Dateien des Verzeichnisses + relevante Aufrufer (`runner/dispatcher.py`, `runner/_runner_tools.py`, `runner/runner.py`, `agents/_defaults.py`, `llm/media_models.py`, `llm/_config.py`).

Dieses Subsystem ist die Tool-Schicht, die ein Agent während seines Tool-Use-Loops aufrufen kann. Jedes Tool ist ein eigenes Modul mit genau einem `TOOL`-Objekt (`datamining.py` ist die Ausnahme: 4 Tools). Eine zentrale Registry (`__init__.py`) sammelt sie ein und liefert dem Runner JSON-Schemas im Anthropic-Format. Daneben liegen im selben Verzeichnis vier **Hilfs-Pipelines** mit `_`-Präfix, die KEINE LLM-Tools sind, sondern intern vom Runner getriggert werden: Memory-Store, Observations-Recording, Compress-Pipeline, Crystallize-Pipeline.

---

## WAS

### Registrierte LLM-Tools (33 Tools in 30 Modulen)

Reihenfolge wie in `_build_registry()` (`__init__.py:48-87`):

1. **shell_exec** (`shell.py`) — Shell-Befehl im Workspace ausführen; gibt stdout/stderr/exit_code zurück. Default-Timeout 60 s (1–600 erlaubt). Setzt automatisch `GH_TOKEN`/`GITHUB_TOKEN` aus dem Projekt-Token. Kategorie `shell`.
2. **file_read** (`file_read.py`) — Datei aus Workspace lesen, mit Zeilennummern. Optionen `offset`/`limit` (Zeilenbereich) und `grep` (Regex, nur passende Zeilen + `context_lines`). Kategorie `files`.
3. **file_write** (`file_write.py`) — Datei schreiben, überschreibt komplett, legt Parent-Verzeichnisse an. Kategorie `files`.
4. **file_patch** (`file_patch.py`) — String-Ersetzung in bestehender Datei. `old_string` muss eindeutig sein (sonst Fehler), `replace_all=true` ersetzt alle. Kategorie `files`.
5. **web_search** (`web_search.py`) — Websuche über lokales SearxNG (`searxng_url` aus Tool-Config). Liefert title/url/snippet, `count` 1–50, language=de fest verdrahtet. Kategorie `web`.
6. **fetch_url** (`fetch_url.py`) — HTTP-Request (GET/POST/PUT/PATCH/DELETE/HEAD) mit transparenter Auth-Injection aus dem Credential-Store; Token kommt NIE im Output zurück. SSRF-geschützt. Max 200 KB Body. Kategorie `web`.
7. **query_fhir_data** (`fhir_data.py`) — Liest FHIR-R4-Patientenakte (Condition, MedicationRequest/Statement, Observation, AllergyIntolerance, Immunization, Procedure, Encounter, DiagnosticReport, DocumentReference, Patient). `resource_types`-Filter + `search_text` Volltext. Kategorie `personal`.
8. **query_health_data** (`health_data.py`) — Apple-Health-Daten (Schritte, Herzfrequenz, Schlaf, Kalorien …) aggregiert über `days` (1–365) + optional `metric`-Filter. Kategorie `personal`.
9. **read_memory** (`read_memory.py`) — Eigene Memory-Notizen lesen. Ohne `key`: Key-Liste (Projekt-gefiltert). Mit `key`: Eintrag direkt (kein Projekt-Filter). `project='*'` = alle Projekte. Kategorie `memory`.
10. **write_memory** (`write_memory.py`) — Memory-Notiz speichern/löschen (`delete=true`). `expires_at` (+2h/+1d/+7d/+4w/ISO), `confidence` (0.0–1.0), `project`. Reinforcement bei Wiederholung, Contradiction-Detection. Kategorie `memory`.
11. **search_memory** (`search_memory.py`) — Substring/Regex-Suche über Key+Content. `max_results` 1–100, `snippet_chars` 20–500, `min_confidence`, `project`, `include_superseded`. Sortiert nach Relevanz × Confidence. Kategorie `memory`.
12. **todo_write** (`todo.py`) — Session-Todo-Liste komplett neu schreiben. `items[].content` + `status` (pending/in_progress/done). Persistiert in `session_state`. Kategorie `tasks`.
13. **send_mail** (`send_mail.py`) — E-Mail via SMTP aus `ctx.config["smtp"]` (host/port/user/password/from/use_tls). Ohne Config: Stub-Fehler. Kategorie `mail`.
14. **list_projects** (`list_projects.py`) — Projekte des Owners mit Workspace-Pfad, Repos, Members, freigegebenen Specialists, samba_enabled. Kategorie `agents`.
15. **list_skills** (`list_skills.py`) — Für den Agent verfügbare Skills (name/description/when_to_use/scope/tools_required). Kategorie `agents`.
16. **load_skill** (`load_skill.py`) — Vollen Skill-Body in den Kontext laden (inkl. sources). Kategorie `agents`.
17. **read_scratchpad** (`read_scratchpad.py`) — Kombiniertes Scratchpad (Tills Zone + Agent-Zone) des Users lesen. Kein Input. Kategorie `scratchpad`.
18. **write_scratchpad** (`write_scratchpad.py`) — Schreibt NUR die Agent-Zone des Scratchpads (ersetzt sie komplett). Tills Zone ist tabu. Kategorie `scratchpad`.
19. **analyze_image** (`analyze_image.py`) — Vision-Input: Bild (lokaler Pfad ≤5 MB oder http-URL) + `question` an ein Vision-Modell (Default `google/gemini-2.5-flash`). Kategorie `media`.
20. **generate_image** (`generate_image.py`) — Text→Bild über OpenRouter chat/completions. `width`/`height`/`transparent` (Green-Screen-Chroma-Key). Default `openai/gpt-5-image-mini`. Kategorie `media`.
21. **generate_music** (`generate_music.py`) — Text→Musik über OpenRouter (Lyria 3, gestreamtes SSE). Default `google/lyria-3-pro-preview`. Kategorie `media`.
22. **generate_speech** (`generate_speech.py`) — Text→Sprache (echtes TTS, verbatim) über OpenRouter `/audio/speech`. `voice`+`model` optional. Kategorie `media`.
23. **generate_video** (`generate_video.py`) — Text→Video über OpenRouter async Jobs-API mit Poll-Loop. `width`/`height`/`duration`/`aspect_ratio`. Default `kling/kling-video-v2-master`. Kategorie `media`.
24. **transcribe_audio** (`transcribe_audio.py`) — Audio→Text via OpenRouter Whisper (`/audio/transcriptions`). ≤25 MB, `language` optional. Default `openai/whisper-large-v3`. Kategorie `media`.
25. **datamining_search** (`datamining.py` → `TOOL_SEARCH`) — Volltextsuche im PostgreSQL-Mirror-Langzeitgedächtnis (vergangene Sessions/Tool-Calls/Gespräche). `event_type`/`agent_name`/`from_date`/`to_date`/`limit` (max 50). Kategorie `memory`.
26. **datamining_semantic** (`datamining.py` → `TOOL_SEMANTIC`) — Semantische Ähnlichkeitssuche (Embeddings). `limit` max 30. Kategorie `memory`.
27. **datamining_timeline** (`datamining.py` → `TOOL_TIMELINE`) — Zeitstrahl aller Sessions gruppiert nach Tag. `from_date`/`to_date`/`agent_name`/`sort` (date|activity)/`limit` (max 500). Kategorie `memory`.
28. **datamining_today** (`datamining.py` → `TOOL_TODAY`) — Übersicht was heute im System passierte. `date` optional. Kategorie `memory`.
29. **ask_agent** (`ask_agent.py`) — **Conditional**: nur registriert wenn `settings.agentlink_url` gesetzt. Beauftragt anderen Agenten über AgentLink (WebSocket) ODER Federation (`persona@workstation` → `/remote/chat`). `task`/`task_type`/`context`/`required_skills`. Kategorie `agents`.
30. **web_browser** (`web_browser.py`) — **Optional/immer angehängt**: Browser-Automation via `dev-browser` (QuickJS-WASM-Sandbox, Playwright/Chromium headless). Führt JS-Script aus, `url` als Convenience-Preamble. Kategorie `web`.
31. **webmin_status** (`webmin_status.py`) — **Optional/immer angehängt**: System-Monitoring vom Webmin-Server via XML-RPC (CPU/RAM/Disk/Load/Uptime/Prozesse), `include_smart` für Disk-Temps. Kategorie `system`.
32. **webmin_call** (`webmin_call.py`) — **Optional/immer angehängt**: beliebige Webmin-Modul-Funktion via XML-RPC (`module::function(args)`). Kategorie `system`.

> Hinweis: `web_browser`, `webmin_status`, `webmin_call` werden in `_build_registry()` IMMER der Registry hinzugefügt (nicht conditional), stehen aber in `OPTIONAL_TOOLS`, damit sie in alten Agent-Configs nicht zu Validation-Fails führen. Nur `ask_agent` ist wirklich conditional zur Registry-Build-Zeit.

### Kategorien (Tally aus dem Quellcode)

`media` (6 Tool-Module: analyze_image, generate_image/music/speech/video, transcribe_audio), `memory` (read/write/search_memory + 4× datamining = 7 Tools), `files` (file_read/write/patch), `agents` (ask_agent, list_projects, list_skills, load_skill), `web` (web_search, fetch_url, web_browser), `system` (webmin_status, webmin_call), `scratchpad` (read/write_scratchpad), `personal` (query_fhir_data, query_health_data), `tasks` (todo_write), `shell` (shell_exec), `mail` (send_mail). Default-Kategorie ist `other` (`base.py:56`, von keinem Tool genutzt).

### Kern-Infrastruktur (keine LLM-Tools)

- **base.py** — `ToolContext`, `ToolResult`, `Tool`-Dataclasses + `ExecuteFn`-Typ.
- **`__init__.py`** — `REGISTRY`, `OPTIONAL_TOOLS`, `list_tools()`, `get_tool()`, `schemas_for()`.
- **_launcher.py** — `Launcher`-Protocol + `DevLauncher` (Subprocess-Spawn für shell_exec). `get_launcher()`/`set_launcher()` (Test-Injection).
- **_path.py** — `safe_path()` + `PathOutsideWorkspace` (Workspace-Sandboxing für file_*).

### Hilfs-Pipelines (interne, vom Runner getriggert)

- **Memory v2**: `_memory_store.py` (Facade) → `_memory_io.py` (File-IO) + `_memory_model.py` (pure Logic).
- **Observations**: `_observations.py` (RawObservation-Recording in JSONL) + `_sessions.py` (Session-Lifecycle-Metadaten).
- **Compress (#61)**: `_compress.py` + `_compress_storage.py` + `_compress_prompts.py`.
- **Crystallize (#62)**: `_crystallize.py` + `_crystallize_storage.py` + `_crystallize_prompts.py`.

### Media-Shared-Helper

- **_openrouter_media.py** — `openrouter_key()`, `save_bytes()`, SSE-Audio-Lesen (`read_audio_sse`, `audio_chunk_from_sse_line`, `is_done_line`), `pcm16_to_wav`, `parse_pcm_content_type`, `synthesize_speech`.
- **_openrouter_video.py** — `submit_video_job`, `poll_video_job`, `download_video`, `_extract_video_url`.
- **_openrouter_transcribe.py** — `transcribe_file` (multipart Whisper-Upload).
- **_image_keying.py** — `chroma_key_green` (Green-Screen → transparentes PNG).
- **_webmin.py** — `resolve_webmin`, `xmlrpc_call`, `_to_json_safe`.

---

## WIE

### Tool-Dispatch (Trigger → Ausführung → DB/Antwort)

1. **LLM emittiert `tool_use`-Block.** Der Runner (`runner.py:64 run()`) baut einmal pro Run einen `ToolContext` (`runner.py:82-84`) aus session_id, agent["id"], session.user_id, dem Workspace und `tool_config` (→ `ctx.config`, `project_id`).
2. **Schemas:** `schemas_for(local_tools)` (`__init__.py:109`) liefert dem LLM `{name, description, input_schema}` im Anthropic-Format. `allowed_tools = local_tools + MCP-Tools` (`runner.py:103`).
3. **Pro Iteration:** `process_tool_uses()` (`_runner_tools.py:22`) läuft über alle tool_uses. Wenn `require_confirm`: `ToolConfirmRequired`-Event + Warten auf User-Entscheidung (`_runner_tools.py:42-56`). `deny` → `ToolResult.fail("Vom Benutzer abgelehnt")`, KEIN record_observation.
4. **`execute_tool()`** (`dispatcher.py:32`):
   - Persistiert IMMER zuerst einen `tool_calls`-Record (`tools_db.create`, `dispatcher.py:50`), auch bei Validation-Fail.
   - Routing: nicht in allowed_tools → fail; `mcp_*`-Präfix → MCP-Bridge; Plugin-Präfix → Plugin-Bridge; nicht in REGISTRY → fail; sonst `REGISTRY[name].execute(args, ctx)` (`dispatcher.py:86-88`).
   - **Alle Exceptions werden gefangen** → `ToolResult.fail("Tool-Crash: <Type>: <msg>")` (`dispatcher.py:89-91`). Der Runner crasht nie an einem Tool.
   - **Redaction-Engstelle:** `redaction.scrub_result(result)` (`dispatcher.py:96`) schwärzt bekannte Secret-Werte BEVOR sie in DB/Transcript/Stream gehen.
   - `tools_db.finish()` schreibt status/duration_ms/error_type/error_message.
5. **record_observation()** (`_runner_tools.py:62`) speichert das Ergebnis als RawObservation (außer bei User-Deny).
6. **to_tool_result_block()** (`dispatcher.py:110`) baut den Anthropic-`tool_result`-Block: `content` (ggf. auf `tool_result_max_chars` gekürzt + DB-Markierung via `mark_truncated`), `is_error`, `tool_name` (fürs Frontend-Card-Rendering), und `media`-Anhänge.

### Media-Result-Handling

`ToolResult.result_type` ∈ {`text`, `image_url`, `audio_url`, `video_url`} (`base.py:25`). URL-basierte Results → `block["media"] = [{kind, url}]`. Lokale Pfade im Output → `extract_media(result, workspace)` zieht Bild/Audio/Video-Pfade. `media`/`tool_name` werden vor dem Anthropic-API-Call wieder weggefiltert (`_ANTHROPIC_ALLOWED` in context.py).

### OpenRouter-Media-Aufrufmuster (3 fundamental verschiedene APIs)

- **Synchron (Bild, Vision):** `POST /chat/completions` mit `modalities:["image","text"]`. Bild kommt als `message.images[].image_url.url` (data-URI ~3 MB). Die data-URI darf NICHT ins LLM → wird im Workspace gespeichert (`_persist_data_uri` → `save_bytes`), nur der Pfad geht zurück. (`generate_image.py:99-225`)
- **Synchron gestreamt (Musik, TTS):** Audio kommt als EINE mehrere MB große SSE-Zeile in `delta.audio.data`. `read_audio_sse` puffert rohe Bytes und trennt selbst an `\n`, weil httpx `aiter_lines()` die Riesenzeile nicht-deterministisch zerlegt. Stream gilt erst mit `[DONE]` als vollständig (`_openrouter_media.py:54-82`, `generate_music.py:95-123`).
- **Async Jobs (Video):** `POST /api/v1/videos` → job_id, dann `GET /api/v1/videos/{id}` pollen. Poll-Loop max 300 s, exponentieller Backoff 5→10→20 s Cap (`generate_video.py:113-151`). URL aus `unsigned_urls[0]` (pre-signed) → sofort downloaden (`_openrouter_video.py:107-133`).
- **Multipart (Transcribe):** `POST /api/v1/audio/transcriptions` multipart `file`+`model` → `{"text":...}` (`_openrouter_transcribe.py:26-61`).

### Green-Screen-Chroma-Key (generate_image transparent=True)

OpenRouter kann keine echte Transparenz. Das Modell malt das Motiv auf reinem Grün (`image_config.background_rgb_color=[0,255,0]` + Prompt-Instruktion `_GREEN_BG_INSTRUCTION`). Danach entfernt `chroma_key_green` das Grün anhand der **Grün-Dominanz** `g - max(r,b)`: ≤40 deckend, ≥100 transparent, dazwischen linear (weiche Kante). Despill deckelt Grün auf `max(r,b)`. Ergebnis immer als PNG mit Alpha (`_image_keying.py`).

### Memory v2 — Datenfluss

- **Speicherort:** `settings.agents_dir / <agent_id> / memory.json` (`_memory_io.py:23`).
- **write_key** (`_memory_io.py:154`) → `_apply_write` (`_memory_io.py:96`): bei vorhandenem Key → Reinforcement (`_reinforce_confidence`: `new = old + 0.1*(1-old)`, Cap 1.0), `reinforcements += 1`. Neu → init confidence (default 0.5). Vor dem Schreiben Contradiction-Detection: `find_contradictions` (Jaccard-Similarity ≥0.7) markiert ähnliche aktive Einträge via `mark_superseded` (`is_latest=False`).
- **Projekt-Sichtbarkeit** (`_project_matches`, `_memory_model.py:107`): `project=None` = global (in allen Projekten sichtbar). `filter_project='*'` = alle. Sonst nur Einträge mit `project==X` ODER global.
- **Expiry** (`_parse_expiry`): `+Nh/+Nd/+Nw/+Nm` (m≈30 d) oder ISO. Abgelaufene werden bei Reads ausgeblendet (`_is_expired`), `cleanup_expired` löscht sie hart (Superseded bleiben als History).
- **Migration** (`_migrate_entry`): String-Einträge und alte Dict-Schemas werden beim Laden rückwärtskompatibel auf das aktuelle Schema gehoben.
- **Bulk-Write** (`write_keys_bulk`): ein Read+Write-Pass für N Einträge (genutzt von Crystallize-Lessons).

### Observations → Compress → Crystallize (3-stufige Pipeline)

1. **Record** (`_observations.record_observation`, `_observations.py:89`): nach JEDEM Tool-Call schreibt der Runner eine RawObservation append-only in `agents/<id>/observations/<session>.jsonl`. tool_input/output werden gekürzt (2000/4000 Zeichen). flock-geschützt. `session_increment_observations` erhöht den Zähler.
2. **Compress (#61)** (`_compress.compress_session`, getriggert in `runner.py:275` am Session-Ende): lädt unkomprimierte Raws, batcht à 30 (`COMPRESS_BATCH_SIZE`), ruft pro Batch EINEN LLM-Call (`call_with_tools` mit leerer Tool-Liste, temperature=0) der ein JSON-Array {type/title/facts/concepts/files/importance/narrative} liefert. Speichert CompressedObservations in `compressed/<session>.jsonl`, markiert Raws via `mark_compressed_bulk` (ein File-Rewrite für die ganze Batch). Bei LLM-Fehler → `fallback_compressed` pro Eintrag.
3. **Crystallize (#62)** (`_crystallize.crystallize_session`): wird automatisch nach Compress getriggert wenn ≥5 (`MIN_OBSERVATIONS`) CompressedObservations vorliegen (als Background-Task `_safe_crystallize`, fehlertolerant via `errors_log.capture`). Baut Chain-Text, LLM liefert {narrative/key_outcomes/files_affected/lessons}. Speichert Crystal append-only in `crystals.jsonl` (versioniert: neueste session-id gewinnt). **Lessons → Memory** als `lesson.<sha256[:12]>`-Keys mit confidence=0.6, `check_contradictions=False` (`_crystallize.py:51-81`).

### fetch_url Auth + SSRF

`_select_cred` (`fetch_url.py:69`): per-User-Credential (`match_credential`) hat Vorrang; nur ohne Match und ohne erzwungenes Profil greift die System-Research-API-Registry (`match_research_api`). `_apply_auth` injiziert bearer/basic/cookie/header/query — der Klartext-Hinweis geht nur ins Logging, NIE ins `tool_result`. SSRF: `is_blocked_host` vor dem Connect + `safe_async_client` pinnt die Connect-IP (DNS-Rebinding-Schutz, #206).

### Webmin XML-RPC

`resolve_webmin` (`_webmin.py:19`) holt das Credential `settings.webmin_credential` aus dem Store, leitet Base-URL aus `settings.webmin_url` oder dem `url_pattern` ab. `xmlrpc_call` POSTet an `/xmlrpc.cgi` mit Basic-Auth (`verify=False`!), erkennt 401/403/HTML-statt-XML und gibt deutsche Fehlertexte zurück. `_to_json_safe` wandelt xmlrpc-Typen JSON-tauglich.

### ask_agent (AgentLink + Federation)

- **`persona@workstation`** → `_execute_federated` → `remote_chat` über Federation-Registry (`ask_agent.py:217`).
- **Sonst AgentLink:** Name→UUID-Normalisierung (`ask_agent.py:104-116`); Project-Agents dürfen nur `allowed_specialists` beauftragen (`ask_agent.py:119-134`). Friendly-Keys (error_log/code_snippet/related_files) werden auf das State-Schema gemappt. `post_state` → `register_pending(state.id, target)` → `asyncio.wait_for(fut, timeout=settings.agentlink_handoff_timeout)`. Nur ein Antwort-State vom beauftragten Ziel löst die Future (#184). Ergebnis aus `working_memory.findings` + `task.description`.

---

## WO

### Foundation / Registry
- `core/src/hydrahive/tools/base.py:8` — `ToolContext` (session_id, agent_id, user_id, workspace, config, project_id)
- `core/src/hydrahive/tools/base.py:19` — `ToolResult` (success, output, error, metadata, result_type) + `.ok()`/`.fail()`/`.to_llm()`
- `core/src/hydrahive/tools/base.py:50` — `Tool`-Dataclass (name, description, schema, execute, category)
- `core/src/hydrahive/tools/__init__.py:48` — `_build_registry()`
- `core/src/hydrahive/tools/__init__.py:82` — conditional `ask_agent` (nur bei `settings.agentlink_url`)
- `core/src/hydrahive/tools/__init__.py:84-86` — `web_browser`/`webmin_status`/`webmin_call` immer angehängt
- `core/src/hydrahive/tools/__init__.py:90` — `REGISTRY`
- `core/src/hydrahive/tools/__init__.py:98` — `OPTIONAL_TOOLS` (ask_agent, web_browser, file_search, dir_list, http_request, webmin_*)
- `core/src/hydrahive/tools/__init__.py:109` — `schemas_for()` (Anthropic-Format)
- `core/src/hydrahive/tools/_launcher.py:32` — `DevLauncher` (Subprocess für shell)
- `core/src/hydrahive/tools/_launcher.py:73-82` — `get_launcher`/`set_launcher`
- `core/src/hydrahive/tools/_path.py:10` — `safe_path()` (Workspace-Sandbox)
- `core/src/hydrahive/tools/_path.py:6` — `PathOutsideWorkspace`

### Dispatch / Runner-Integration
- `core/src/hydrahive/runner/runner.py:82` — `ToolContext`-Konstruktion
- `core/src/hydrahive/runner/runner.py:98-103` — local_tools/mcp/plugin-Schemas + allowed_tools
- `core/src/hydrahive/runner/runner.py:275` — `compress_session()`-Trigger am Session-Ende
- `core/src/hydrahive/runner/dispatcher.py:32` — `execute_tool()`
- `core/src/hydrahive/runner/dispatcher.py:50` — `tools_db.create` (immer)
- `core/src/hydrahive/runner/dispatcher.py:57-91` — Routing (allowed/MCP/Plugin/REGISTRY/Crash-Catch)
- `core/src/hydrahive/runner/dispatcher.py:96` — `redaction.scrub_result`
- `core/src/hydrahive/runner/dispatcher.py:110` — `to_tool_result_block()` (Truncation + media)
- `core/src/hydrahive/runner/_runner_tools.py:22` — `process_tool_uses()`
- `core/src/hydrahive/runner/_runner_tools.py:42-56` — Confirmation-Flow
- `core/src/hydrahive/runner/_runner_tools.py:62` — `record_observation`
- `core/src/hydrahive/agents/_defaults.py:6` — `_BASE_TOOLS` (master/project/specialist Default-Tool-Listen)
- `core/src/hydrahive/agents/_defaults.py:29` — `_filtered()` (filtert nicht-registrierte raus)
- `core/src/hydrahive/agents/_defaults.py:58` — `DEFAULT_TOOLS`

### Einzelne Tools
- `core/src/hydrahive/tools/shell.py:42-80` — `_resolve_gh_token` (Projekt-Token-Lookup)
- `core/src/hydrahive/tools/shell.py:90-104` — `_STATIC_ENV_DENYLIST` + `_env_denylist` (Secret-Schutz)
- `core/src/hydrahive/tools/shell.py:123-130` — `_BLOCKED_MMX_SPEECH`/`_MMX_MUSIC_GEN`-Rewrite
- `core/src/hydrahive/tools/shell.py:166` — `TOOL` (shell_exec)
- `core/src/hydrahive/tools/file_read.py:30` — `_grep_lines`; `:97` — `TOOL`
- `core/src/hydrahive/tools/file_write.py:47` — `TOOL`
- `core/src/hydrahive/tools/file_patch.py:49-55` — Eindeutigkeits-Check; `:70` — `TOOL`
- `core/src/hydrahive/tools/web_search.py:28` — `searxng_url`-Lookup; `:57` — `TOOL`
- `core/src/hydrahive/tools/fetch_url.py:46` — `_apply_auth`; `:69` — `_select_cred`; `:94-123` — SSRF; `:151` — `TOOL`
- `core/src/hydrahive/tools/web_browser.py:69-95` — dev-browser-Spawn + HOME-Override; `:138` — `TOOL`
- `core/src/hydrahive/tools/fhir_data.py:40` — `_format_resource`; `:119` — `TOOL`
- `core/src/hydrahive/tools/health_data.py:33-34` — `health_api_key`-Gate; `:57` — `TOOL`
- `core/src/hydrahive/tools/read_memory.py:73` — `TOOL`
- `core/src/hydrahive/tools/write_memory.py:88` — `write_key`-Aufruf; `:118` — `TOOL`
- `core/src/hydrahive/tools/search_memory.py:76` — `load_filtered`; `:112` — Score; `:148` — `TOOL`
- `core/src/hydrahive/tools/todo.py:55` — `session_state.set`; `:60` — `TOOL`
- `core/src/hydrahive/tools/send_mail.py:27` — `_send_sync`; `:45` — `ctx.config["smtp"]`; `:74` — `TOOL`
- `core/src/hydrahive/tools/list_projects.py:63` — `TOOL`
- `core/src/hydrahive/tools/list_skills.py:36` — `TOOL`
- `core/src/hydrahive/tools/load_skill.py:49` — `TOOL`
- `core/src/hydrahive/tools/read_scratchpad.py:18` — `TOOL`
- `core/src/hydrahive/tools/write_scratchpad.py:30-33` — `save_agent` + `ScratchpadTooLarge`; `:36` — `TOOL`
- `core/src/hydrahive/tools/analyze_image.py:69` — `_image_to_content_block`; `:170` — `TOOL`
- `core/src/hydrahive/tools/generate_image.py:84-92` — Green-BG-Instruktion; `:166` — `_extract_image_url`; `:199` — `_persist_data_uri`; `:228` — `TOOL`
- `core/src/hydrahive/tools/generate_music.py:106` — `read_audio_sse`; `:135` — `TOOL`
- `core/src/hydrahive/tools/generate_speech.py:59` — `synthesize_speech`; `:74` — `TOOL`
- `core/src/hydrahive/tools/generate_video.py:104-151` — submit + Poll-Loop; `:154` — `TOOL`
- `core/src/hydrahive/tools/transcribe_audio.py:59` — `_mime_for`; `:106` — `transcribe_file`; `:117` — `TOOL`
- `core/src/hydrahive/tools/datamining.py:64` — `_search`; `:82` — `_semantic`; `:98` — `_timeline`; `:154` — `_today`; `:165/:177/:188/:202` — die 4 `TOOL_*`
- `core/src/hydrahive/tools/ask_agent.py:81` — `_execute`; `:104-134` — UUID-Norm + Specialist-Gate; `:189` — `register_pending`; `:217` — `_execute_federated`; `:248` — `TOOL`
- `core/src/hydrahive/tools/webmin_status.py:39` — `xmlrpc_call`; `:52` — `TOOL`
- `core/src/hydrahive/tools/webmin_call.py:76-77` — `module::function`; `:95` — `TOOL`

### Shared Media-Helper
- `core/src/hydrahive/tools/_openrouter_media.py:24` — `openrouter_key`; `:54` — `read_audio_sse`; `:85` — `save_bytes`; `:93` — `pcm16_to_wav`; `:116` — `synthesize_speech`
- `core/src/hydrahive/tools/_openrouter_video.py:28` — `submit_video_job`; `:72` — `poll_video_job`; `:107` — `_extract_video_url`; `:136` — `download_video`
- `core/src/hydrahive/tools/_openrouter_transcribe.py:26` — `transcribe_file`
- `core/src/hydrahive/tools/_image_keying.py:34` — `chroma_key_green`; `:22-23` — `_THRESHOLD=40`/`_SOFTNESS=60`
- `core/src/hydrahive/tools/_webmin.py:19` — `resolve_webmin`; `:38` — `xmlrpc_call`; `:83` — `_to_json_safe`

### Memory v2
- `core/src/hydrahive/tools/_memory_store.py:9-39` — Re-Export-Facade
- `core/src/hydrahive/tools/_memory_io.py:23` — `_memory_file` (Pfad)
- `core/src/hydrahive/tools/_memory_io.py:56` — `load_filtered`; `:96` — `_apply_write`; `:154` — `write_key`; `:182` — `write_keys_bulk`; `:212` — `delete_key`; `:221` — `list_keys`; `:236` — `cleanup_expired`
- `core/src/hydrahive/tools/_memory_model.py:16-18` — Konstanten; `:71` — `_parse_expiry`; `:89` — `_reinforce_confidence`; `:94` — `_jaccard_similarity`; `:107` — `_project_matches`; `:131` — `find_contradictions`; `:151` — `mark_superseded`

### Observations / Sessions
- `core/src/hydrahive/tools/_observations.py:36` — `_obs_file` (JSONL-Pfad); `:41` — `_exclusive_lock`; `:89` — `record_observation`; `:126` — `list_raw_observations`; `:190` — `mark_compressed_bulk`
- `core/src/hydrahive/tools/_sessions.py:35` — `_session_file`; `:59` — `session_start`; `:92` — `session_end`; `:124` — `session_increment_observations`; `:134` — `session_list`
- `core/src/hydrahive/tools/_observations.py:28-29` — Truncate-Limits (4000/2000)

### Compress / Crystallize
- `core/src/hydrahive/tools/_compress.py:42` — `_compress_batch`; `:88` — `compress_session`; `:116-134` — Auto-Crystallize-Trigger
- `core/src/hydrahive/tools/_compress_storage.py:16` — `_compressed_file`; `:20` — `save_compressed`; `:27` — `load_compressed`
- `core/src/hydrahive/tools/_compress_prompts.py:21` — `COMPRESS_BATCH_SIZE=30`; `:23` — `COMPRESS_SYSTEM`; `:49` — `build_batch_prompt`; `:69` — `parse_batch_response`; `:111` — `fallback_compressed`
- `core/src/hydrahive/tools/_crystallize.py:38` — `MIN_OBSERVATIONS=5`; `:51` — `_save_lessons`; `:84` — `crystallize_session`
- `core/src/hydrahive/tools/_crystallize_storage.py:17` — `_crystals_file`; `:22` — `save_crystal`; `:49` — `list_crystals`; `:80` — `get_crystal`
- `core/src/hydrahive/tools/_crystallize_prompts.py:15` — `CRYSTALLIZE_SYSTEM`; `:36` — `build_chain_text`; `:66` — `fingerprint`; `:81` — `parse_llm_response`

### Externe SSOTs / Settings (von Tools genutzt)
- `core/src/hydrahive/settings/_paths.py:20` — `data_dir` (`HH_DATA_DIR`, default `/var/lib/hydrahive2`)
- `core/src/hydrahive/settings/_paths.py:27` — `agents_dir` (= data_dir/agents — Wurzel für memory/observations/compressed/crystals/sessions)
- `core/src/hydrahive/settings/_services.py:47` — `agentlink_url`; `:66` — `agentlink_agent_id`; `:81` — `agentlink_handoff_timeout`; `:129` — `health_api_key`
- `core/src/hydrahive/settings/_infra.py:70` — `webmin_url`; `:75` — `webmin_credential`
- `core/src/hydrahive/llm/media_models.py:32-38` — `DEFAULTS`; `:69` — `get_media_model`; `:122` — `voices_for`
- `core/src/hydrahive/llm/_config.py:19` — `provider_env_vars`; `:45` — `apply_keys`; `:64` — `openrouter_key`
- `core/src/hydrahive/credentials/store.py:78` — `get_credential`; `:113` — `match_credential`
- `core/src/hydrahive/credentials/redaction.py:146` — `scrub_result`
- `core/src/hydrahive/research/store.py:95` — `match_research_api`
- `core/src/hydrahive/net/ssrf.py:19` — `SsrfBlocked`; `:55` — `is_blocked_host`; `:167` — `safe_async_client`

---

## WARUM

### Annahmen & Invarianten
- **Ein Tool = ein Modul = ein `TOOL`-Objekt.** Die Registry importiert statisch (`__init__.py:13-43`). Ein neues Tool muss in BEIDEN angefasst werden: Modul anlegen UND in `_build_registry()` eintragen UND (für Default-Sichtbarkeit) in `_defaults._BASE_TOOLS`. Drei Stellen — bewusst, weil die Registry den Schema-Export für den LLM steuert und `_BASE_TOOLS` nur die Default-Zuweisung pro Agent-Typ.
- **`ToolResult` ist immer JSON-serialisierbar** (`asdict(result)` landet in `tool_calls`-DB, `dispatcher.py:103`). Deshalb `output: Any`, aber `to_llm()` macht daraus immer einen String.
- **Workspace-Sandbox ist NUR über `safe_path`** durchgesetzt — und nur file_read/write/patch nutzen es. shell_exec hat KEINEN Pfad-Guard (läuft im Workspace-cwd, kann aber überall hin). Das ist Absicht laut CLAUDE.md (Home-Lab, vertraute Agenten mit voller Tool-Macht); `DevLauncher` dokumentiert das explizit (`_launcher.py:32-38`).
- **Secret-Schutz hat zwei Schichten:** (1) `shell.py:_env_denylist` entfernt Provider-Keys + JWT/DSN aus dem Subprocess-ENV, damit `echo $OPENROUTER_API_KEY` nichts liefert. (2) `redaction.scrub_result` (`dispatcher.py:96`) schwärzt bekannte Secret-WERTE aus JEDEM Tool-Output, egal wie sie reinkamen. Wenn man Schicht 1 anfasst (neuer Provider), muss der Key über `_ENV_MAP`/`provider_env_vars()` gehen — sonst rutscht er durch (wie früher OpenRouter, Kommentar `shell.py:88-89`).
- **Media-data-URIs dürfen NIE ins LLM-Kontext.** Sie sind ~3 MB base64 — würden Tokens fressen und den Cache sprengen. Deshalb persistieren alle generate_*-Tools ins Workspace (`save_bytes` → `ctx.workspace/generated`, von `/api/files` ausgeliefert) und geben nur den Pfad zurück. Wenn man das ändert, explodieren Token-Kosten.
- **Memory-Project-Default ist `None` = global.** `write_memory` macht KEINEN Kontext-Fallback (`write_memory.py:85` — explizit `project=None` wenn nicht angegeben), aber Reads filtern über `ctx.project_id`. Heißt: ein Eintrag ohne `project` ist überall sichtbar, ein Eintrag mit `project=X` nur in X + bei `*`. Beim Update wird `project` nur aktualisiert wenn explizit übergeben (`_memory_io.py:132`) — sonst bleibt die alte Zuordnung.
- **Observations sind append-only JSONL mit flock.** Nie die ganze Datei pro Tool-Call neu schreiben (`_observations.py:37`). `mark_compressed_bulk` macht EINEN Rewrite für die ganze Batch — das Single-Pattern (`mark_compressed`) ist nur ein Wrapper und wird in Schleifen ausdrücklich gewarnt (`_observations.py:181-187`).
- **Crystallize läuft als fehlertoleranter Background-Task** (`_compress.py:124-134`). Schlägt es fehl, ist das nicht fatal — die Session endet trotzdem. `errors_log.capture(reraise=False)` schluckt den Fehler bewusst.
- **`ask_agent` ist conditional weil ein Stub-Tool Loop-Detection triggert** (`__init__.py:49-51`, #13). Ein immer-fehlschlagendes Tool verschwendet Iterationen, weil der Master es wiederholt versucht.
- **Compress/Crystallize-LLM-Calls laufen mit leerer Tool-Liste, temperature=0** (`_compress.py:55-62`) — reiner Text-in/JSON-out, deterministisch. JSON-Parsing fällt pro Eintrag auf `fallback_*` zurück, damit ein Format-Ausrutscher nicht die ganze Pipeline killt.
- **Lessons werden mit `check_contradictions=False` geschrieben** (`_crystallize.py:72`), weil sie generalisierte Insights sind — sie sollen sich NICHT gegenseitig als veraltet markieren.

### Was bricht wenn man X anfasst
- **`ToolContext`-Felder umbenennen** → jedes Tool bricht (alle lesen `ctx.workspace`/`ctx.user_id`/`ctx.agent_id`/`ctx.config`/`ctx.project_id`).
- **`settings.agents_dir`-Pfad ändern** → Memory, Observations, Compressed, Crystals, Sessions liegen alle darunter; Pfad-Drift verliert das gesamte Agent-Gedächtnis. (Memory-Test-Gotcha: `data_dir` friert via `cached_property` ein → Test-Memory MEMORY.md.)
- **`OpenRouter`-Response-Format** (`message.images[]`, `delta.audio.data`, `unsigned_urls`) → die Extractoren (`_extract_image_url`, `audio_chunk_from_sse_line`, `_extract_video_url`) sind exakt darauf abgestimmt, haben aber Fallback-Pfade für ältere/undokumentierte Felder.
- **`redaction.scrub_result` entfernen/umgehen** → Secrets aus Tool-Output landen in DB + Transcript + Frontend-Stream.

---

## Datenmodell

### Dateien pro Agent (alle unter `settings.agents_dir/<agent_id>/`)
| Pfad | Format | Inhalt | Geschrieben von |
|------|--------|--------|-----------------|
| `memory.json` | JSON dict | Memory v2 (key → MemoryEntry) | `_memory_io.save` |
| `observations/<session>.jsonl` | JSONL append | RawObservations | `record_observation` |
| `observations/<session>.lock` | leer | flock-Datei | `_exclusive_lock` |
| `compressed/<session>.jsonl` | JSONL append | CompressedObservations | `save_compressed` |
| `crystals.jsonl` | JSONL append (versioniert) | Crystals (Session-Digests) | `save_crystal` |
| `sessions/<session>.json` | JSON | Session-Metadaten | `_save_session_file` |

### MemoryEntry-Schema (`_memory_model.py:25-53`)
`content` (str), `created_at`, `updated_at`, `expires_at` (ISO|None), `confidence` (float 0.0–1.0, default 0.5), `reinforcements` (int), `last_reinforced_at`, `is_latest` (bool), `superseded_by` (key|None), `superseded_at`, `supersedes` (list[key]), `project` (str|None — None=global).
Konstanten: `_CONFIDENCE_DEFAULT=0.5`, `_CONFIDENCE_STEP=0.1`, `_CONTRADICTION_THRESHOLD=0.7` (Jaccard).

### RawObservation (`_observations.py:103-114`)
`id` (`obs_<ms>_<hex>`), `session_id`, `agent_id`, `timestamp`, `hook_type` (`post_tool_use`|`post_tool_failure`|`conversation`), `tool_name`, `tool_input` (≤2000 Z.), `tool_output` (≤4000 Z.), `compressed` (bool), `compressed_id`.

### CompressedObservation (`_compress.py:72-80` + `_compress_prompts.py`)
`id` (`cobs_<ms>_<hex>`), `session_id`, `agent_id`, `raw_observation_id`, `timestamp`, `type` (file_read|file_write|command_run|decision|discovery|error|other), `title` (≤80), `facts` (≤5), `concepts` (≤8 lowercase), `files`, `importance` (1–10), `narrative` (≤500).

### Crystal (`_crystallize.py:151-163`)
`id` (`crys_<ms>_<hex>`), `session_id`, `agent_id`, `project`, `created_at`, `narrative` (≤200), `key_outcomes` (≤8), `files_affected` (dedupliziert), `lessons` (≤5), `source_observation_ids`, `observation_count`. Lessons zusätzlich als Memory-Key `lesson.<sha256[:12]>` (confidence 0.6).

### Session (`_sessions.py:76-87`)
`id`, `agent_id`, `project`, `started_at`, `ended_at`, `status` (active|completed|abandoned|paused), `observation_count`, `model`, `first_prompt` (≤500), `summary`.

### ToolResult / ToolContext (`base.py`)
`ToolResult`: success, output (Any), error, metadata (dict), result_type (text|image_url|audio_url|video_url).
`ToolContext`: session_id, agent_id, user_id, workspace (Path), config (dict), project_id (str|None).

### Config-Keys in `ctx.config` (aus `tool_config`)
- `searxng_url` (web_search), `smtp` (send_mail: host/port/user/password/from/use_tls), `project_id` (→ `ctx.project_id`), `media_models.{image,music,tts,transcribe,video}` (von `get_media_model(cat, config)`, ABER siehe Offene Enden).

### Env-Vars / Settings
- `HH_DATA_DIR` (→ data_dir/agents_dir), `HH_HEALTH_API_KEY` (health_data-Gate), `HH_AGENTLINK_URL` (ask_agent-Registrierung), `HH_WEBMIN_URL`, Webmin-Credential-Name (`settings.webmin_credential`).
- shell-Denylist (`_STATIC_ENV_DENYLIST`): `HH_SECRET_KEY`, `HH_JWT_SECRET`, `HH_PG_MIRROR_DSN`, `HH_DATABASE_URL`, `HH_AGENTLINK_TOKEN`, `DISCORD_BOT_TOKEN`, `MINIMAX_API_KEY` + dynamisch `provider_env_vars()`.
- Auto-gesetzte ENV im shell_exec: `GH_TOKEN`, `GITHUB_TOKEN` (aus Projekt-Token).

### DB-Tabellen (extern, von Dispatch/Datamining genutzt)
- `tool_calls` (`tools_db.create/finish/mark_truncated`, `dispatcher.py`) — jeder Tool-Call mit args/result/status/duration/error.
- `session_state` (todo_write → `session_state.set(session_id, "todos", …)`).
- PostgreSQL-Mirror (`mirror_query.search_events`/`list_sessions`) — Quelle für die 4 datamining_*-Tools.
- FHIR-DB (`db.fhir.query_fulltext`/`query_by_type`/`timeline`), Health-DB (`db.health.get_metrics_summary`).

---

## Offene Enden

1. **`web_search` und `send_mail` sind faktisch tot/Stub im Default-Pfad.** Beide lesen aus `ctx.config` (`searxng_url` bzw. `smtp`), aber KEIN Runner-Aufrufer befüllt `tool_config` mit diesen Keys — alle `runner.run(...)`-Calls (`handoff_receiver.py:137`, `_agent_glue.py:156`, `_session_msg_helpers.py:54/56`, `sessions_messages.py:202`) übergeben gar kein `tool_config` oder nur `extra_system`. `ctx.config` ist also leer → `web_search` antwortet „SearxNG nicht konfiguriert", `send_mail` antwortet „send_mail ist aktuell ein Stub". `send_mail` steht trotzdem in den master-Default-Tools (`_defaults.py:11`). Die echte Mail-Pipeline läuft separat über `communication/mail/` (`smtp_send.py`, eigene `smtp_*`-Config aus `settings.mail_*`) — das Tool ist eine zweite, unverbundene Implementierung. **Drift: zwei SMTP-Implementierungen, eine davon tot.**
2. **`get_media_model` wird ohne `config` aufgerufen.** Die Tools rufen `get_media_model("image")` etc. ohne 2. Argument (`generate_image.py:110`, `generate_music.py:86`, `generate_speech.py:57`, `generate_video.py:97`, `transcribe_audio.py:98`). Die Funktion unterstützt `config`-Override (`media_models.py:69`), bekommt ihn aber nie → es greifen IMMER die `DEFAULTS`, nie die per-`llm.json` gewählten `media_models`. Der dokumentierte Config-Hebel ist im Tool-Pfad nicht verdrahtet.
3. **Default-TTS-Modell-Drift:** `media_models.DEFAULTS["tts"] = "hexgrad/kokoro-82m"` (`media_models.py:36`), aber `generate_speech` hat keinen eigenen `_DEFAULT_MODEL` und verlässt sich auf `get_media_model("tts")`. `generate_image._DEFAULT_MODEL`, `generate_video._DEFAULT_MODEL`, `transcribe_audio._DEFAULT_MODEL` duplizieren dagegen die Defaults lokal im Modul-Header UND in der Schema-Beschreibung — drei Quellen für denselben Default-Wert, die auseinanderlaufen können.
4. **Tote/entfernte Tools in `OPTIONAL_TOOLS`:** `file_search`, `dir_list`, `http_request` (`__init__.py:98`) sind entfernte Tools, die nur noch toleriert werden, damit alte Agent-Configs nicht failen. Die zugehörigen `.pyc` liegen noch im `__pycache__` (`file_search`, `dir_list`, `http_request`, `crystallize`), die `.py` sind weg. Aufräum-Kandidat.
5. **`record_observation` läuft synchron im Tool-Loop** und macht pro Call einen flock + Session-File-Read+Write (`session_increment_observations`, `_sessions.py:124`). Bei vielen Tool-Calls wird das Session-JSON wiederholt komplett neu geschrieben — nicht append-only wie die Observations selbst.
6. **Known-Limitation-Kommentare im Code:** `list_raw_observations` lädt die komplette JSONL in RAM (`_observations.py:136-138`, „bei 1000+ Observations eng"); `session_list` glob't alle Session-Dateien vor `limit` (`_sessions.py:145-147`). Beide als „für aktuellen Scope irrelevant" markiert.
7. **`xmlrpc_call` nutzt `verify=False`** (`_webmin.py:54`) — TLS-Verifikation für Webmin (self-signed Zertifikate auf Port 10000) bewusst aus. Sicherheits-Tradeoff, dokumentiert nur implizit.
8. **`web_browser` braucht externes `dev-browser`-Binary** (`npm install -g dev-browser`). Ohne Installation: sofortiger Fehler. Schreibt nach `~/.config/hh-dev-browser-home` (HOME-Override, weil `/home/hydrahive` read-only). Hard-Dependency, die nicht über die normale Tool-Config geprüft wird.
9. **`shell_exec` MMX-Hard-Block** (`shell.py:123-141`): `mmx speech/tts` ist per Regex gesperrt (fraß früher das TTS-Tageskontingent), `mmx music generate` bekommt automatisch `--model music-2.6` angehängt. Diese Sonderlogik ist eine implizite Kopplung an ein externes CLI (`mmx`) im generischen Shell-Tool — fragil wenn sich das mmx-Interface ändert.
10. **`ask_agent` Federation vs. AgentLink** sind zwei getrennte Pfade im selben Tool (`_execute` vs. `_execute_federated`). Federation braucht `db.federation` + `federation.registry.remote_chat`; AgentLink braucht `settings.agentlink_url` + `hydrahive.agentlink`. Das Tool ist aber nur conditional registriert, wenn `agentlink_url` gesetzt ist — d.h. **reine Federation ohne AgentLink würde das Tool gar nicht erst sichtbar machen** (`__init__.py:82`), obwohl der Federation-Pfad AgentLink nicht braucht. Mögliche Lücke.
11. **`mark_compressed` (Single)** existiert nur als Wrapper um `mark_compressed_bulk` mit explizitem Anti-Pattern-Warnhinweis (`_observations.py:181-187`) — wird nirgends produktiv aufgerufen außer im Wrapper selbst. Toter Komfort-Pfad.
