# Datamining (Langzeitgedächtnis)

Das Datamining-Subsystem ist HydraHives **Langzeitgedächtnis**: ein PostgreSQL-Mirror,
in den *jede* Message blockweise als „Events" gespiegelt wird (fire-and-forget), plus
ein Lese-Stack (Volltext + semantische Suche, Sessions, Timeline, Graph), ein
Import-Stack (SQLite/Git/JSONL/Logs/Shell/GitHub/Gitea), ein Embedding-/Backfill-Stack
(pgvector), Token-Statistik, DB-Transfer (pg_dump/restore/merge) und ein
Live-Ingest-Pfad für externe Claude-Code-Instanzen. Der Mirror ist ein **kompletter
No-op**, wenn `HH_PG_MIRROR_DSN` nicht gesetzt ist.

---

## WAS

### Backend — HTTP-Endpoints (Router `datamining.py`, Prefix `/api/datamining`)
- `GET /api/datamining/events?limit=100` — letzte N Events (Live-Feed). `limit` gecappt auf 500. Antwort `{active, events}`. `datamining.py:21`
- `GET /api/datamining/search` — Volltext- **oder** semantische Suche (`semantic=true`). Filter: `q`, `event_type`, `agent_name`, `username`, `from_date`, `to_date`, `limit` (≤100). Antwort `{active, results, error}`. `datamining.py:27`
- `GET /api/datamining/sessions` — Session-Liste (aggregiert aus `events`). Filter: `agent_name`, `username`, `from_date`, `to_date`, `limit` (≤500). `datamining.py:59`
- `GET /api/datamining/sessions/{session_id}` — Session-Detail mit chunk-gemergten Events; 404 wenn nicht gefunden. `datamining.py:81`
- `GET /api/datamining/graph` — **System-Topologie** (Agenten/User/Tools + Kanten), nicht der Embedding-Graph. Delegiert an `mirror_graph_topology.build_topology()`. `datamining.py:89`
- `GET /api/datamining/embed/status` — Embedding-Fortschritt `{active, sessions, total, embedded, pending, model, backfill_running}`. `datamining.py:95`
- `POST /api/datamining/embed/reset?event_type=` — setzt `embedding/embedding_model/embedded_at` auf NULL (optional pro `event_type`), damit Backfill neu rechnet. `datamining.py:100`
- `POST /api/datamining/embed/rechunk` — schneidet zu lange `tool_result`-Events neu in `CHUNK_CHARS`-Blöcke; läuft im Hintergrund. `datamining.py:106`
- `POST /api/datamining/embed/backfill` — startet den Embedding-Backfill-Task (prüft `_backfill_running`, braucht konfiguriertes `embed_model`). `datamining.py:117`
- `POST /api/datamining/ingest` (**admin-only**) — nimmt vorgeparste Claude-Code-Session-Events (`_IngestRequest`) und schreibt sie direkt in `events` (`ON CONFLICT DO NOTHING`). `datamining.py:160`
- `POST /api/datamining/import/sqlite` + `GET .../status` — SQLite→PG-Import (Hintergrund). `datamining.py:187` / `:198`
- `POST /api/datamining/import/git?repo_path=` + `GET .../status` — Git-Log-Import. `datamining.py:204` / `:216`
- `POST /api/datamining/import/jsonl` + `GET .../status` — JSONL-Token-Usage-Import → `llm_calls`. `datamining.py:222` / `:232`
- `POST /api/datamining/import/logs?nginx_log=&journal_unit=&journal_lines=` + `GET .../status` — Nginx/Journal-Import. `datamining.py:238` / `:253`
- `POST /api/datamining/import/shell-history?username=` (UploadFile) — Shell-History-Import (sofort, kein Hintergrund). `datamining.py:259`

### Backend — Issues-Import (Router `datamining_issues.py`, Prefix `/api/datamining/import`)
- `POST /api/datamining/import/github` (**admin-only**) — GitHub-Issues+PRs+Kommentare importieren. `datamining_issues.py:207`
- `POST /api/datamining/import/gitea` (**admin-only**) — Gitea-Issues+PRs+Kommentare importieren (default base `http://192.168.3.22:3001`). `datamining_issues.py:217`

### Backend — Stats (Router `datamining_stats.py`, Prefix `/api/datamining/stats`)
- `GET /api/datamining/stats/daily?agent_id=&days=` — Token-Zeitreihe pro Tag (≤90 Tage). `datamining_stats.py:20`
- `GET /api/datamining/stats/latest?count=` — letzte N Sessions mit Token-Kurzstats (≤50). `datamining_stats.py:30`
- `GET /api/datamining/stats/session/{session_id}` — Token-Detail einer Session; 404 wenn fehlt. `datamining_stats.py:36`
- `GET /api/datamining/stats/agent/{agent_id}?days=` — Agent-Aggregat inkl. Top-Tools (≤90 Tage). `datamining_stats.py:44`

### Backend — Transfer (Router `datamining_transfer.py`, Prefix `/api/datamining`, alle **admin-only**)
- `POST /api/datamining/export` + `GET .../export/status` + `GET .../export/download` — `pg_dump --format=custom --compress=9` → herunterladbarer Dump. `datamining_transfer.py:35` / `:45` / `:55`
- `POST /api/datamining/import` + `GET .../import/status` — `pg_restore --clean --if-exists` (zerstörerischer Voll-Restore). `datamining_transfer.py:67` / `:80`
- `POST /api/datamining/import-merge` + `GET .../import-merge/status` — **nicht-destruktiver** Merge-Import via COPY→Temp-Table→`INSERT … ON CONFLICT DO NOTHING`. `datamining_transfer.py:85` / `:98`

### Backend — Agenten-Tools (Memory-Kategorie, registriert in `tools/__init__.py:77-80`)
- `datamining_search` — Volltextsuche im Langzeitgedächtnis. `tools/datamining.py:165`
- `datamining_semantic` — semantische Ähnlichkeitssuche (pgvector). `tools/datamining.py:177`
- `datamining_timeline` — Sessions gruppiert nach Tag, sort `date|activity`. `tools/datamining.py:188`
- `datamining_today` — Übersicht „was heute passiert ist". `tools/datamining.py:202`

### Backend — MCP-Tools (`mcp-servers/hydrahive-api/server.py`, dünne REST-Wrapper)
- `hh_dm_search` → `GET /api/datamining/search`. `server.py:125`
- `hh_dm_get_session` → `GET /api/datamining/sessions/{id}`. `server.py:140`
- `hh_dm_list_sessions` → `GET /api/datamining/sessions` (entpackt `.sessions`). `server.py:146`
- `hh_dm_stats` → `GET /api/datamining/stats/latest`. `server.py:152`

### Backend — Live-Ingest-Endpoint (extern; `sessions_messages.py`)
- `POST /api/sessions/{session_id}/log` (`LogIngestBody`) — hängt **eine** Message an + löst Mirror aus; **kein** Agenten-Lauf, idempotent über `message_id`. Owner-Check. `sessions_messages.py:224`

### Live-Ingest-Hook (`hooks/datamining-sync/`, läuft außerhalb des Core auf der externen Instanz)
- `sync.py` — Claude-Code `Stop`/`SubagentStop`-Hook, liest Transkript, POSTet neue Einträge, fail-safe. `sync.py:82`
- `client.py` — synchroner httpx-REST-Client (`ensure_session`, `log`, Login/Bearer). `client.py:11`
- `transcript.py` — Transkript-JSONL → Message-Dicts (nur user/assistant). `transcript.py:7`
- `state.py` — Sidecar-State pro CC-Session (`hh_session_id` + Set bereits gesendeter IDs), atomarer Write. `state.py:18`
- `redact.py` — best-effort Secret-Redaction (API-Keys/Bearer/`HH_PASS`). `redact.py:26`

### Nachtanalyse / Card-Konsolidierung (an Datamining angedockt)
- `zahnfee` — Nacht-Analytikerin: liest Datamining-Events der letzten N Stunden → Morgen-Briefing (LLM, JSON). Endpoints `/api/zahnfee/*`. `zahnfee/runner.py:112`
- `cards.consolidate` — verdichtet Mirror-Sessions zu Gist-Cards (proaktiver Recall L2), getriggert vom Zahnfee-Tages-Tick. `cards/consolidate.py:121`

### Frontend — UI-Komponenten (`frontend/src/features/datamining/`)
- `DataminingPage.tsx` — Tab-Container (`feed/search/sessions/stats/graph`) + Toolbar (Export/Import/Merge/SQLite/Shell/Issues/Quellen). `DataminingPage.tsx:17`
- `LiveFeedTab.tsx` — Live-Feed, Auto-Poll alle 5s. `LiveFeedTab.tsx:9`
- `SearchTab.tsx` — Suchformular, Event-Type-Filter, Semantik-Toggle. `SearchTab.tsx:11`
- `SessionsTab.tsx` — Session-Tabelle → öffnet `SessionDrawer`. `SessionsTab.tsx:9`
- `SessionDrawer.tsx` — Session-Detail mit expandierbaren Events. `SessionDrawer.tsx:14`
- `StatsTab.tsx` — Token-Zeitreihe, letzte Sessions, Session-/Agent-Detailpanels. `StatsTab.tsx:236`
- `GraphTab.tsx` — 3D-Force-Graph (react-force-graph-3d) der Topologie, Live-Aktiv-Marker alle 10s. `GraphTab.tsx:44`
- `_EmbedStatusBar.tsx` — Embedding-Fortschrittsbalken + Backfill/Reset/Rechunk-Buttons. `_EmbedStatusBar.tsx:12`
- `_IssueImportForm.tsx` — GitHub/Gitea-Issue-Import-Formular + Buttons. `_IssueImportForm.tsx:12` / `:40`
- `_SourceImportButtons.tsx` — Ein-Klick Git/JSONL/Logs-Import mit Backend-Defaults. `_SourceImportButtons.tsx:18`
- `api.ts` — REST-Client für alle obigen Endpoints. `api.ts:15`
- `types.ts` — `DmEvent`/`DmSession`/`DmSessionDetail`, `TYPE_COLORS`, Zeitformatierer. `types.ts:1`

### Config-Flags / Env-Vars (siehe Datenmodell)
- `HH_PG_MIRROR_DSN` — Master-Schalter; ohne ihn ist *alles* No-op.
- `embed_model` (in `llm.json`) — steuert Embedding-Spalten-Dimension + Suche/Backfill.
- Hook-Env: `HH_BASE_URL`, `HH_API_KEY`/`HH_USER`+`HH_PASS`, `HH_AGENT_ID`, `HH_VERIFY_SSL`, `HH_SYNC_STATE_DIR`.

---

## WIE

### Datenfluss A — nativer Schreib-Pfad (Message → Mirror)
1. `messages.append(...)` schreibt in SQLite (`INSERT OR IGNORE`). Nur wenn `inserted` (rowcount>0) wird der Mirror angestoßen. `messages.py:42-51`
2. `mirror.schedule_message(m, s)` — **sync, fire-and-forget**: erzeugt einen `asyncio`-Task `write_message`. Kein laufender Loop → still verworfen (`except RuntimeError: pass`). `mirror.py:182`
3. `write_message(pool, m, s)` ruft `explode(m, s)` → Liste Event-Dicts, `executemany INSERT … ON CONFLICT (id) DO NOTHING`, dann `queue_embed(pool, events)`. `_mirror_writes.py:34`
4. `explode` zerlegt Blocks: `text`→`user_input|assistant_text`, `thinking`→`thinking`, `tool_use`→`tool_call`, `tool_result`→ **gechunkt** in `CHUNK_CHARS=3000`-Blöcke (je ein `tool_result`-Event mit `chunk_index/chunk_total`); `role=="compaction"` → ein `compaction`-Event. Event-ID-Schema: `f"{message_id}:{block_index}:{chunk_index}"`. `_mirror_explode.py:15`
5. `queue_embed` plant pro Event mit Inhalt einen `embed_event`-Task (nur wenn `embed_model` konfiguriert). `_mirror_embed.py:14`
6. `embed_event` → `aembed(text, model)` → `UPDATE events SET embedding=…::vector WHERE id=$ AND embedding IS NULL`. `_mirror_embed.py:41`

Parallel wird `sessions.create/update` → `mirror.schedule_session` → `write_session` (UPSERT in `sessions`). `mirror.py:192`, `_mirror_writes.py:15`

### Datenfluss B — Live-Ingest externer Claude-Code-Instanzen
1. Claude-Code feuert `Stop`/`SubagentStop` → `sync.py:main()` liest JSON-Payload von stdin (`session_id`, `transcript_path`). `sync.py:82`
2. `run_sync` nimmt **fcntl-Lock pro `cc_session_id`** (serialisiert parallele Stop/SubagentStop, verhindert Doppel-HH-Sessions). `sync.py:46-55`
3. `parse_entries` filtert Transkript auf user/assistant mit stabiler `uuid` als `message_id`; `redact_entries` scrubbt Secrets. `transcript.py:7`, `redact.py:45`
4. State laden (`hh_session_id` + `synced_ids`). Fehlt `hh_session_id` → `client.ensure_session(agent_id, title)` = `POST /api/sessions` → **State sofort persistieren** (sonst zweite HH-Session beim nächsten Lauf). `sync.py:59-66`
5. Nur ungesendete Einträge (`message_id ∉ seen`) → `client.log` = `POST /api/sessions/{id}/log` je Eintrag; Zwischen-Checkpoint alle `SAVE_EVERY=100`. `sync.py:69-78`
6. Serverseitig: `log_ingest` → `messages.append(message_id=…, created_at=…)` → Datenfluss A. Doppelte Idempotenz: SQLite `INSERT OR IGNORE` + Mirror `ON CONFLICT DO NOTHING`. `sessions_messages.py:224`

`HH_AGENT_ID` ist die **uuid4** eines vorab angelegten Agenten; `agent_name(agent_id)` löst sie im Mirror auf den `name` auf. Falscher/fehlender Agent → `create_session` 404 → Hook überspringt still (fail-safe).

### Datenfluss C — Volltextsuche
`search_events(semantic=False)` → `_text_search`: `WHERE text ILIKE %q% OR tool_output ILIKE … OR tool_input::text ILIKE … OR tool_name ILIKE …`, plus optionale Filter, `ORDER BY created_at DESC LIMIT`. Snippet = `left(coalesce(text, tool_output, tool_input::text, ''), 300)`. `_mirror_search.py:91`

### Datenfluss D — semantische Suche
`_semantic_search`: `aembed(q, model, embed_type="query")` → Vektor-Literal `[a,b,c]`, `WHERE embedding IS NOT NULL …`, `ORDER BY embedding <=> $vec::vector` (Cosine-Distanz), Similarity = `1 - (embedding <=> vec)`. Braucht `embed_model`, sonst `ValueError`. `_mirror_search.py:121`

### Datenfluss E — Session-Detail mit Chunk-Merging
`get_session_detail` holt Session-Meta (aus `sessions`, Fallback aggregiert aus `events`) + alle Events `ORDER BY created_at, block_index, chunk_index`, dann `_merge_chunks`: Events mit gleichem `(message_id, block_index)` werden text-/output-konkateniert → ein logisches Event. `_mirror_sessions.py:82`, `:126`

### Datenfluss F — Embedding-Backfill (Batch)
`_run_backfill` → `backfill_loop(pool, model, batch_size)`: holt Events `WHERE embedding IS NULL AND (text/tool_output/tool_input nicht leer) ORDER BY created_at LIMIT batch_size`, baut `tool_name: content`-Texte (gekappt `_MAX_TEXT_CHARS=24000`), embedded in Sub-Batches `_EMBED_BATCH=32` via `aembed_batch`, speichert pro Event nur wenn noch NULL. Abbruch wenn ein Batch 0 speichert (API-Fehler). `_mirror_embed.py:79`

### Datenfluss G — Rechunk
`run_rechunk` findet `(message_id, block_index)`-Paare mit irgendeinem `tool_result`-Chunk länger als `CHUNK_CHARS`, lädt alle Chunks, konkateniert, re-chunkt, `DELETE` der alten + `INSERT` der neuen (Embeddings gehen verloren → Backfill nötig). `_datamining_rechunk.py:11`

### Datenfluss H — Topologie-Graph
`build_topology` aggregiert aus `events`: Agenten (DISTINCT session_id), User, Tools (`event_type='tool_call'`, Top 60), Kanten User↔Agent + Agent→Tool, plus `active_agents` (`created_at > NOW() - 60s`). Node-`val` = skalierte Session-/Use-Counts. `mirror_graph_topology.py:12`

### Datenfluss I — DB-Merge (nicht-destruktiv)
`_run_import_merge`: `pg_restore --data-only --file=` → roh-SQL, `_query_target_cols` fragt vorhandene Zielspalten ab (filtert z.B. `embedding` weg), `_copy_via_temp_table` wandelt jedes `COPY tbl …` in `BEGIN; CREATE TEMP TABLE _mg_tbl …; COPY _mg_tbl …; INSERT INTO tbl SELECT … ON CONFLICT DO NOTHING; DROP TABLE; COMMIT;` um, zählt Zeilen vor/nach via asyncpg, fährt mit `psql ON_ERROR_STOP=1`. `datamining_transfer.py:244`, `:155`

### Zustandsmaschinen / Hintergrund-Singletons
- Mirror-State global im Modul: `_pool`, `_backfill_running`, `_backfill_task`. `mirror.py:42-44`
- Jeder Importer hat ein eigenes Modul-globales `_running`/`_progress` (single-flight, kein Lock). `mirror_import_*.py`
- Transfer-States: `_export_state`/`_import_state`/`_merge_import_state` (Modul-Dicts). `datamining_transfer.py:23-25`
- Mirror-Lifecycle: `pg_mirror.init()` in `lifespan` (nur wenn DSN gesetzt), `pg_mirror.close()` beim Shutdown. `api/lifespan.py:91`, `:203`

---

## WO

### Routen / Router
- `core/src/hydrahive/api/routes/datamining.py:16` — `router` (Prefix `/api/datamining`), `Auth = require_auth`.
- `core/src/hydrahive/api/routes/datamining_issues.py:18` — `router` (Prefix `/api/datamining/import`), admin-only.
- `core/src/hydrahive/api/routes/datamining_stats.py:15` — `router` (Prefix `/api/datamining/stats`).
- `core/src/hydrahive/api/routes/datamining_transfer.py:19` — `router` (Prefix `/api/datamining`), admin-only.
- Registrierung: `core/src/hydrahive/api/main.py:135-138` (datamining/_issues/_stats/_transfer), `:148` (zahnfee).
- Live-Ingest-Route: `core/src/hydrahive/api/routes/sessions_messages.py:224` (`log_ingest`), Pydantic `LogIngestBody` `:215`.

### Mirror-Kern (`core/src/hydrahive/db/`)
- `mirror.py:49` `init()` / `:83` `close()` / `:127` `reset_embeddings()` / `:147` `_run_backfill()` / `:160` `recent_events()` / `:182` `schedule_message()` / `:192` `schedule_session()` / `:102` `on_embed_model_change()` / `:115` `_start_backfill()`.
- `mirror_query.py:8` — Public Facade (re-exportiert `embed_status`, `search_events`, `list_sessions`, `get_session_detail`).
- `_mirror_search.py:27` `embed_status()` / `:67` `search_events()` / `:91` `_text_search()` / `:121` `_semantic_search()` / `:11` `_dt()` / `:22` `_pool()`.
- `_mirror_sessions.py:12` `list_sessions()` / `:62` `event_type_counts()` / `:82` `get_session_detail()` / `:126` `_merge_chunks()` / `:159` `_finalize()`.
- `_mirror_embed.py:14` `queue_embed()` / `:30` `embed_text()` / `:41` `embed_event()` / `:60` `_store_batch()` / `:79` `backfill_loop()`. Konstanten `_EMBED_BATCH=32` `:10`, `_MAX_TEXT_CHARS=24000` `:11`.
- `_mirror_explode.py:15` `explode()` / `:83` `_chunks()` / `:89` `agent_name()` / `:97` `parse_ts()`. Konstante `CHUNK_CHARS=3000` `:12`.
- `_mirror_writes.py:15` `write_session()` / `:34` `write_message()`.
- `_mirror_ddl.py:9` `DDL_TABLES` / `:161` `DDL_VIEW` (`session_metrics`) / `:207` `ensure_embed_col()`.

### Embedding-Graph (anders als Topologie — derzeit ungenutzt von der UI)
- `mirror_graph.py:19` `build_graph()` (UMAP+HDBSCAN+Cosine-Edges, `MAX_NODES=3000`, `EDGE_THRESHOLD=0.82`, `TOP_K_EDGES=3`). `:131` `_umap_hdbscan()`, `:159` `_cosine_edges()`.
- Topologie-Graph (von `/graph` genutzt): `mirror_graph_topology.py:12` `build_topology()`.

### Importer (`core/src/hydrahive/db/`)
- `mirror_import_sqlite.py:24` `run_sqlite_import()` / `:20` status / `:82` `_explode_row()` / `:114` `_insert_events()`.
- `mirror_import_git.py:32` `run_git_import()` / `:65` `_read_git_log()` / `:103` `_commit_to_row()` (event_type `git_commit`, session_id `git-history`).
- `mirror_import_jsonl.py:26` `run_jsonl_import()` / `:56` `_parse_jsonl()` / `:124` `_guess_provider()` → `llm_calls`.
- `mirror_import_logs.py:40` `run_logs_import()` / `:75` `_parse_nginx()` / `:111` `_parse_journal()` (event_types `http_request`/`service_log`, session_id `system-logs`).
- `mirror_import_shell.py:33` `parse_history()` / `:87` `run_shell_import()` (event_type `shell_command`, session_id `shell-history`, `_SENSITIVE_RE` skippt Secret-Befehle).

### Rechunk / Transfer
- `core/src/hydrahive/api/routes/_datamining_rechunk.py:11` `run_rechunk()`.
- `core/src/hydrahive/api/routes/datamining_transfer.py:103` `_run_export()` / `:126` `_run_import()` / `:244` `_run_import_merge()` / `:155` `_copy_via_temp_table()` / `:222` `_query_target_cols()` / `:152` `_COPY_RE`. Exports-Dir `:21` (`settings.data_dir / "exports"`).

### Token-Stats
- `core/src/hydrahive/db/token_stats.py:17` `session_stats()` / `:67` `latest_sessions()` (SQLite-Quelle, liest `messages.metadata`-JSON).
- `core/src/hydrahive/db/token_stats_agg.py:10` `daily_stats()` / `:74` `agent_stats()` (Top-Tools aus `tool_calls`).

### Agenten-Tools / Cards / Zahnfee
- `core/src/hydrahive/tools/datamining.py:64` `_search` / `:82` `_semantic` / `:98` `_timeline` / `:154` `_today`; Tool-Objekte `:165`–`:202`. Registriert `tools/__init__.py:77-80`.
- `core/src/hydrahive/db/_mirror_cards.py:52` `upsert_card()` / `:142` `top_cards_for()` (Recall A) / `:167` `search_cards()` (Recall C) / `:126` `wipe_cards()`.
- `core/src/hydrahive/db/_mirror_cards_model.py:13` `Card` / `:35` `derive_groundedness()`.
- `core/src/hydrahive/cards/consolidate.py:62` `consolidate_session()` / `:121` `consolidate_recent()`.
- `core/src/hydrahive/zahnfee/runner.py:15` `_fetch_events()` / `:112` `run()`; Scheduler `zahnfee/scheduler.py:11`; Config `zahnfee/config.py:36`; Storage `zahnfee/storage.py:16`.

### Live-Ingest-Hook (`hooks/datamining-sync/`)
- `sync.py:23` `_session_lock()` / `:46` `run_sync()` / `:82` `main()`; `SAVE_EVERY=100` `:43`.
- `client.py:11` `HiveClient` (`ensure_session` `:35`, `log` `:42`).
- `transcript.py:7` `parse_entries()`.
- `state.py:18` `load_state()` / `:33` `save_state()`.
- `redact.py:26` `redact_text()` / `:45` `redact_entries()` (`_FULL`/`_PREFIXED` Muster `:15`/`:20`).

### Frontend (`frontend/src/features/datamining/`)
- `DataminingPage.tsx:14` `TABS`, `:17` Komponente; Tab-Komponenten `LiveFeedTab.tsx:9`, `SearchTab.tsx:11`, `SessionsTab.tsx:9`, `SessionDrawer.tsx:14`, `StatsTab.tsx:236`, `GraphTab.tsx:44`.
- `_EmbedStatusBar.tsx:12`, `_IssueImportForm.tsx:12`/`:40`, `_SourceImportButtons.tsx:18`.
- `api.ts:15` `dataminingApi`; `types.ts:1` Typen + `TYPE_COLORS:44`.

### MCP
- `mcp-servers/hydrahive-api/server.py:125` `hh_dm_search` / `:140` `hh_dm_get_session` / `:146` `hh_dm_list_sessions` / `:152` `hh_dm_stats`; Impl `mcp-servers/hydrahive-api/tools/datamining.py`.

### Settings
- `core/src/hydrahive/settings/_services.py:93` `pg_mirror_dsn` (`HH_PG_MIRROR_DSN`).
- `core/src/hydrahive/settings/_paths.py:20` `data_dir` / `:24` `config_dir` / `:28` `agents_dir` / `:69` `numba_cache_dir` / `:79` `sessions_db` / `:87` `llm_config`.

---

## WARUM

- **Mirror ist fire-and-forget und No-op-by-default.** `schedule_message`/`schedule_session` schlucken `RuntimeError` (kein Loop) still — der Mirror darf den Haupt-Schreibpfad **nie** blockieren oder zum Scheitern bringen. Folge: Schreibt man Messages außerhalb eines laufenden Event-Loops (z.B. ein sync-Endpoint im Threadpool), landet **nichts** im Datamining. Genau deshalb **muss `log_ingest` async sein** (Doku im Docstring, `sessions_messages.py:230-239`) — ein sync-`def` würde den Mirror-Task verwerfen und nur SQLite füllen.
- **Event-ID = `{message_id}:{block_index}:{chunk_index}`** ist die Invariante, die alle Schreib-/Import-Pfade idempotent macht (`ON CONFLICT (id) DO NOTHING`). Wer dieses Schema in `explode` ändert, bricht Dedup über alle Importe + den Rechunk hinweg.
- **`agent_id` = uuid4 des Agenten, nicht frei wählbar.** Der Live-Ingest-Hook braucht eine **existierende** Agent-UUID (`HH_AGENT_ID`), sonst gibt `create_session` 404 und der Hook überspringt still. Im Mirror wird die UUID via `agent_name(agent_id)` (liest `agents/{id}/config.json`) auf den Anzeigenamen aufgelöst. Falsche UUID = leeres/falsches Datamining ohne Fehlermeldung.
- **fcntl-Lock pro CC-Session** im Hook ist die Lösung für eine real beobachtete Race: parallel feuernde `Stop`+`SubagentStop` riefen beide `ensure_session`, bevor der State eine `hh_session_id` hielt → mehrere HH-Sessions pro CC-Session. Der Lock + sofortiges Persistieren der Session-ID verhindert das.
- **State als ID-Set, nicht als Offset-Zähler** (`state.py`): robust gegen Umordnung/Einschübe im Transkript. Ein Offset würde eine in der Mitte eingefügte Message überspringen.
- **`session_metrics`-View in eigenem try-except** (`mirror.py:63-68`): `CREATE OR REPLACE VIEW` braucht Ownership; gehört der View einem anderen DB-User, scheitert das — aber die Tabellen-DDL ist da schon committed, der Mirror läuft weiter. Der View fehlt bewusst `tool_calls/successes` (Kommentar `_mirror_ddl.py:162`): die SQLite-Quelle ist für Tool-Telemetrie authoritative, der PG-View nur für LLM/Compaction/Errors.
- **Embedding-Spalte ist dynamisch dimensioniert** (`ensure_embed_col`): die Dimension kommt aus `embed_model` (`dim_for_model`). Ändert sich das Modell, wird die Spalte **gedroppt + neu angelegt** (alle Embeddings weg) und ein Backfill muss laufen. `on_embed_model_change` (vom LLM-Save-Endpoint, `routes/llm.py`) cancelt laufenden Backfill, passt `events`+`cards` an und startet neu. `table` ist whitelisted (`events`/`cards`) — nie User-Input, weil per f-string in SQL interpoliert.
- **Embedding ist „nur wenn NULL"** (`UPDATE … WHERE embedding IS NULL`): verhindert teures Doppel-Embedding und macht Backfill restart-sicher.
- **Topologie vs. Embedding-Graph:** `/graph` liefert `build_topology` (billig, SQL-Aggregat über `events`), **nicht** `build_graph` (teures UMAP/HDBSCAN). `build_graph` existiert, wird aber von keinem Endpoint/keiner UI aufgerufen — siehe Offene Enden.
- **Merge-Import behält natives COPY-Format** statt INSERT-pro-Zeile (schnell, kein Quoting), routet aber über Temp-Tables mit `ON CONFLICT DO NOTHING`, und filtert Quellspalten auf real existierende Zielspalten (z.B. `embedding` aus einem Dump mit pgvector landet nicht in einer DB ohne die Spalte). Der zerstörerische `/import` dagegen macht `pg_restore --clean --if-exists` — kippt die Ziel-DB.
- **Rechunk verliert Embeddings:** das INSERT in `run_rechunk` schreibt keine `embedding`-Spalte → neu gechunkte Events sind unembedded und brauchen Backfill. Bewusster Trade-off; deshalb sitzt der Rechunk-Button neben Backfill in der Status-Bar.
- **Token-Stats lesen SQLite, nicht den Mirror.** `token_stats*` greifen `messages.metadata`/`tool_calls` aus der lokalen SQLite-DB ab — sie funktionieren auch ohne aktiven Mirror, decken aber nur native Sessions ab (nicht importierte/externe). Der Mirror-`llm_calls`-Pfad (JSONL-Import + `session_metrics`-View) ist eine **zweite, getrennte** Token-Quelle.
- **`embed_text` stellt `tool_name:` voran** — damit Tool-Calls/-Results semantisch nach Tool auffindbar bleiben; das gleiche Präfix muss im Backfill repliziert werden (`backfill_loop` baut es separat), sonst driften Live- und Backfill-Embeddings auseinander.

---

## Datenmodell

### PostgreSQL-Mirror-Tabellen (DDL: `_mirror_ddl.py:9`)

**`sessions`** — Mirror der Session-Metadaten (UPSERT). Spalten: `id` PK, `username`, `agent_id`, `agent_name`, `project_id`, `title`, `status`, `started_at`, `updated_at`, `mirrored_at` (default `now()`).

**`events`** — Kern. Eine Zeile pro Block/Chunk. Spalten:
`id` PK (`{msg}:{block}:{chunk}`), `message_id`, `session_id`, `block_index`, `chunk_index` (default 0), `chunk_total` (default 1), `username`, `agent_id`, `agent_name`, `project_id`, `event_type`, `text`, `tool_name`, `tool_use_id`, `tool_input` (JSONB), `tool_output`, `is_error`, `token_count`, `created_at`, `mirrored_at`, plus dynamisch: `embedding` (`vector(dim)`), `embedding_model`, `embedded_at`.
Indizes: `events_session`, `events_message(message_id,block_index,chunk_index)`, `events_user(username,created_at)`, `events_type(event_type,created_at)`, `events_tool(tool_name) WHERE NOT NULL`, plus `events_embedding_hnsw` (oder `_ivfflat`-Fallback) auf `embedding vector_cosine_ops`.

**`llm_calls`** — Token/Kosten-Telemetrie (befüllt v.a. via JSONL-Import). Spalten u.a.: `id` PK, `session_id`, `created_at`, `agent_id`, `user_id`, `provider`, `model`, `temperature`, `max_tokens`, `reasoning_effort`, `prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `stop_reason`, `ttft_ms`, `total_ms`, `cost_micros`, `turn_in_session`. Indizes auf session/created/agent/user/model.

**`compaction_events`** — Compaction-Telemetrie (~30 Spalten: `triggered_by`, `trigger_threshold_pct`, `skipped`, `skip_reason`, `messages_*`, `tokens_*`, `cut_*`, `summary_*`, `facts_count`, `duration_ms`, `error`, …). `_mirror_ddl.py:76`

**`errors_log`** — `id`, `created_at`, `session_id`, `agent_id`, `user_id`, `source`, `severity` (default `error`), `error_type`, `error_message`, `traceback`, `context` (JSONB). `_mirror_ddl.py:114`

**`cards`** — abgeleitete Gist-Cards (proaktiver Recall). `card_id` PK (`card:{session_id}`), `session_id`, `gist`, `valence` (good|bad|neutral), `salience` (high|low), `groundedness` (observed|claimed|mixed), `topics` (JSONB), `agent_id/agent_name/username`, `created_at` (Session-Zeit), `source` (JSONB), `confidence` (v2), `superseded_by`/`supersedes` (v2 JSONB), `schema_version` (default 1), `computed_at` (`now()`), `consolidation_model`, + dynamisch `embedding/embedding_model/embedded_at`. Indizes `cards_session`, `cards_agent`, `cards_recency_salience`. `_mirror_ddl.py:133`

**View `session_metrics`** (`_mirror_ddl.py:161`) — aggregiert je Session: `llm_calls`, `input/output/cache_*_tokens`, `cost_micros`, `total_llm_ms`, `compactions`, `compactions_skipped`, `errors`. Kein `tool_calls` (bewusst).

### Event-Typen (`event_type`-Werte)
- Native (aus `explode`): `user_input`, `assistant_text`, `thinking`, `tool_call`, `tool_result`, `compaction`. `_mirror_explode.py`
- Import: `git_commit` (Git), `http_request` + `service_log` (Logs), `shell_command` (Shell), `github_issue`/`github_pr` + `*_comment`, `gitea_issue`/`gitea_pr` + `*_comment` (Issues).
- Frontend-Filter (`SearchTab.tsx:9`) + `TYPE_COLORS` (`types.ts:44`) kennen nur die 6 nativen Typen.

### SQLite-Quelle (für Token-Stats)
`messages.metadata` (JSON) — `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`, `tool_calls`, `compaction`. Plus `tool_calls`-Tabelle (für Top-Tools). `token_stats.py`

### Config / Env-Vars
- `HH_PG_MIRROR_DSN` (`_services.py:94`) — Postgres-DSN; leer ⇒ Mirror aus.
- `embed_model` in `llm.json` (`settings.llm_config`, `llm/_config.py:load_config`) — steuert Vektordimension + Suche/Backfill.
- `HH_DATA_DIR` (default `/var/lib/hydrahive2`) → `exports/`, `sessions.db`, `agents/`, `zahnfee_briefing.json`, `.numba-cache`.
- `HH_CONFIG_DIR` (default `/etc/hydrahive2`) → `zahnfee.json`, `llm.json`.
- `HH_NUMBA_CACHE` — Cache für UMAP/HDBSCAN (Embedding-Graph).
- Hook-Env (`hooks/datamining-sync/README.md`): `HH_BASE_URL`, `HH_API_KEY` **oder** `HH_USER`+`HH_PASS`, `HH_AGENT_ID` (Pflicht, Agent-UUID), `HH_VERIFY_SSL` (default 1), `HH_SYNC_STATE_DIR` (default `~/.claude/datamining-sync`).
- Zahnfee-Config (`zahnfee.json`): `enabled`, `model`, `run_hour` (default 3), `lookback_hours` (default 24), `source_datamining`, `source_mail`, `soul`.

---

## Offene Enden

- **`build_graph` (Embedding-Graph, `mirror_graph.py`) ist tot.** `/api/datamining/graph` ruft `build_topology` auf; `build_graph` (UMAP/HDBSCAN/Cosine-Edges, ~190 Zeilen, Deps `umap`/`hdbscan`/`numpy`) wird von keinem Endpoint und keiner UI aufgerufen. Entweder verdrahten oder entfernen. Die Frontend-`api.ts:134` `graph()` ist als `unknown` getypt und `GraphTab` interpretiert die Antwort als Topologie — d.h. der teure Graph wäre ohnehin inkompatibel.
- **Git-Import ohne `repo_path` crasht.** `datamining.py:211` greift `settings.repo_dir` **oder** `settings.hh_repo_dir` — **keines existiert** im Settings-Objekt (`_paths.py` hat weder). `hasattr(settings,"repo_dir")` ist False ⇒ `settings.hh_repo_dir` ⇒ `AttributeError`. Funktioniert nur, wenn der Aufrufer explizit `repo_path` übergibt; die UI (`startGitImport`) tut das **nicht** (sendet leeren Body) → Ein-Klick-Git-Import ist faktisch kaputt.
- **`mirror_import_sqlite.py` importiert `_parse_ts` doppelt + ungenutzt.** `_explode_row` (`:83`) importiert `_parse_ts`, nutzt es aber nicht (das spätere `_insert_events` importiert es erneut `:115`). Toter Import.
- **Tool-Schema vs. Realität:** `datamining_search` listet im Schema nur `user_input|assistant_text|tool_call|tool_result` als `event_type` (`tools/datamining.py:23`) — `thinking`/`compaction`/Import-Typen fehlen, obwohl sie im Index existieren.
- **Frontend kennt nur native Event-Typen.** `SearchTab` Filter + `TYPE_COLORS` decken die 6 nativen Typen ab; importierte Events (`git_commit`, `http_request`, `github_issue`, …) bekommen Default-Grau und sind nicht filterbar.
- **`reset_embeddings`/Rechunk verlieren Daten ohne Backup-Hinweis.** `reset` nullt **alle** Embeddings, Rechunk löscht+neu-inserted Events ohne Embedding — beides erzwingt einen vollen Backfill; die UI-Buttons (↺/✂) haben nur Tooltips, keine Bestätigung.
- **Gitea-Import nur `state=open`, GitHub `state=all`.** Asymmetrie (`datamining_issues.py:158` vs `:92`) — geschlossene Gitea-Issues/PRs werden nicht importiert.
- **Hook-README widersprüchlich zur Redaction.** `README.md:48-51` sagt „Redaction … hier bewusst noch nicht enthalten", aber `redact.py` existiert und `sync.py:56` ruft `redact_entries` aktiv auf. Doku driftet hinter dem Code her.
- **Doppelter `/import`-Namespace-Konflikt vermeidbar?** `datamining.py` (`/api/datamining/import/sqlite|git|jsonl|logs|shell-history`) und `datamining_transfer.py` (`/api/datamining/import`, `/import/status`) und `datamining_issues.py` (`/api/datamining/import/github|gitea`) teilen sich den `/import`-Prefix über drei Router — funktioniert (verschiedene Subpfade), ist aber leicht zu verwechseln; `GET /import/status` (Transfer) vs `GET /import/sqlite/status` (datamining) leben nebeneinander.
- **`agent_name(agent_id)` liest pro Aufruf das File-System** (`agents/{id}/config.json`, `_mirror_explode.py:89`) — kein Cache; bei großen Importen/Hochfrequenz-Writes ein FS-Read pro Event-Batch (write_session/explode). Potenzieller Hotspot.
- **`numba_cache_dir`/UMAP-Pfad** wird nur vom toten `build_graph` gebraucht — solange der ungenutzt bleibt, ist `HH_NUMBA_CACHE` + die `umap`/`hdbscan`-Dependency totes Gewicht.
- **MCP `hh_dm_stats` ≠ inhaltliche „Stats".** Mappt auf `/stats/latest` (letzte Sessions), nicht auf `daily`/`agent`-Aggregate — der Name verspricht mehr als der Endpoint liefert.
