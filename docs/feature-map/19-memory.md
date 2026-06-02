# Memory & Cards (Recall)

> Subsystem-Landkarte für das Gedächtnis von HydraHive2. Drei getrennte, aber
> verzahnte Gedächtnis-Schichten leben hier:
>
> 1. **Memory v2** — kuratiertes, agent-geschriebenes Key/Value-Gedächtnis
>    (`memory.json` pro Agent, lokale Datei). Tools `read_memory` /
>    `write_memory` / `search_memory`, plus Confidence/Reinforcement/Expiry/
>    Contradiction-Detection/Projekt-Scoping. Read-API für den Browser.
> 2. **Observation-Pipeline** — Raw-Observations (Capture pro Tool-Call) →
>    CompressedObservations (LLM-Batch) → Crystals (Session-Digest + Lessons).
>    Agent-lokale JSONL-Dateien. Lessons fließen zurück ins Memory v2.
> 3. **Proaktiver Recall (Cards)** — abgeleitete, recompute-safe Gist-Cards aus
>    den Datamining-Mirror-Sessions (PostgreSQL/pgvector), nächtlich von der
>    Zahnfee konsolidiert (L2), beim Session-Start (Recall A) und cue-getriggert
>    (Recall C) in den System-Prompt gewoben (L3). Strikt getrennt vom
>    kuratierten Memory.
>
> Der „grüne Elefant" ist Tills kognitives Modell hinter Schicht 3:
> capture → konsolidieren MIT Denken → mit Verifikation abrufen (Mensch-Analogie:
> tagsüber roh lernen, nachts grob sortieren, im Review prüfen, beim Abruf nur die
> geprüfte Essenz). v1 baut nur capture+konsolidieren+billiger Recall; das
> Verify-/Contradiction-Reasoning ist bewusst v2 und ungebaut.
> Quelle: `docs/superpowers/specs/2026-05-29-proactive-recall-design.md`.

---

## WAS

### Tools (Agent-Tools, an die LLM gegeben)

- **`read_memory`** — Liest die eigenen Memory-Notizen. Ohne `key` → Key-Liste
  (gefiltert nach aktivem Projekt + globalen Einträgen). Mit `key` → Eintrag
  direkt (kein Projekt-Filter). Mit `project='*'` → alle Projekte. Blendet
  abgelaufene + veraltete Einträge aus. Datei `tools/read_memory.py`.
- **`write_memory`** — Speichert/aktualisiert eine Notiz unter `key`. `delete=true`
  entfernt. `expires_at` setzt Ablauf (relativ `+2h/+1d/+7d/+4w` oder ISO).
  Wiederholtes Schreiben auf denselben Key erhöht Confidence (Reinforcement).
  Ähnliche Einträge werden automatisch als veraltet markiert (Contradiction
  Detection). `project` ordnet einem Projekt zu (ohne → global sichtbar).
  Datei `tools/write_memory.py`.
- **`search_memory`** — Sucht in eigenen Notizen nach Phrase (case-insensitiv, über
  Key UND Content). Pro Treffer Key + Snippet rund um den Match. Sortiert nach
  Relevanz × Confidence. Default: nur aktives Projekt + global, ohne Abgelaufene/
  Veraltete. Params: `regex`, `max_results` (1–100), `snippet_chars` (20–500),
  `min_confidence` (0.0–1.0), `project` (`'*'`=alle), `include_superseded`.
  Datei `tools/search_memory.py`.
- **`crystallize_session`** — (Agent kann direkt aufrufen) Kristallisiert eine
  Session: alle CompressedObservations → Crystal (Session-Digest) + Lessons.
  `force=True` ignoriert die MIN_OBSERVATIONS-Schwelle und überschreibt einen
  bestehenden Crystal. Datei `tools/_crystallize.py:crystallize_session`.
- **Kategorie** aller drei Memory-Tools: `category="memory"`
  (`tools/read_memory.py:73`, `tools/write_memory.py:118`, `tools/search_memory.py:148`).

### Memory-Tool-Parameter (Config-Flags pro Aufruf)

- `read_memory`: `key`, `project` (`read_memory.py:16-30`)
- `write_memory`: `key` (required), `content`, `delete`, `expires_at`,
  `confidence`, `project` (`write_memory.py:16-55`)
- `search_memory`: `query` (required), `regex`, `max_results`, `snippet_chars`,
  `min_confidence`, `project`, `include_superseded` (`search_memory.py:15-56`)

### API-Endpoints (Memory-View, gemountet unter `/api/agents`)

- **`GET /api/agents/{agent_id}/memory`** — Memory-Browser. Query: `project`, `q`
  (Substring auf Key+Content), `include_expired`, `limit` (1–2000, default 200).
  Auth: `require_auth` + `check_agent_access`. (`agent_memory.py:35-93`)
- **`DELETE /api/agents/{agent_id}/memory/{key:path}`** — Eintrag löschen.
  204 No Content. **Nur Admin** (`require_admin`). (`agent_memory.py:107-118`)
- **`GET /api/agents/{agent_id}/crystals`** — Crystal-Liste (Session-Digests).
  Query: `project`, `limit` (1–200, default 20). (`agent_memory.py:125-158`)
- **`GET /api/agents/{agent_id}/memory-sessions`** — Session-Liste mit
  observation_count + has_crystal-Flag. Query: `project`, `limit` (1–500,
  default 50). (`agent_memory.py:165-205`)
- **`GET /api/agents/{agent_id}/memory-sessions/{session_id}/observations`** —
  CompressedObservations einer Session (für den Session-Drawer im Frontend).
  (`agent_memory.py:212-244`)
- Router-Prefix `/api/agents`, Tag `memory`, registriert in
  `api/main.py:13` + `api/main.py:106`.

### Backend-Funktionen (Card/Recall-Kern)

- **`consolidate_session(session_id, model)`** — Eine Mirror-Session → eine Card
  (idempotent via `upsert_card`). (`cards/consolidate.py:62`)
- **`consolidate_recent(lookback_hours, model, limit=200)`** — Batch: alle
  Mirror-Sessions im Zeitfenster → Cards, gibt Anzahl zurück.
  (`cards/consolidate.py:121`)
- **`_llm_tags(events, model)`** — Ein LLM-Call → geparste Card-Tags
  (gist/valence/salience/topics). Claude-Prefill-Logik.
  (`cards/consolidate.py:29`)
- **`upsert_card(card, embedding)`** — Schreibt/aktualisiert Card idempotent
  (ON CONFLICT card_id). (`db/_mirror_cards.py:52`)
- **`get_card(card_id)`** — Eine Card lesen (ohne Embedding-Spalte).
  (`db/_mirror_cards.py:111`)
- **`wipe_cards()`** — Löscht ALLE Cards (wipe-and-rebuild der abgeleiteten
  Schicht). Berührt nur `cards`-Tabelle. (`db/_mirror_cards.py:126`)
- **`top_cards_for(agent_id, limit=8)`** — Recall A: Top-N Cards nach
  recency × salience. (`db/_mirror_cards.py:142`)
- **`search_cards(query, limit=5)`** — Recall C: pgvector-Cosine-Suche über
  `cards.embedding`. (`db/_mirror_cards.py:167`)
- **`derive_groundedness(tool_result_count, assistant_text_count)`** — v1-Heuristik
  observed/claimed/mixed aus Event-Typ-Mix. (`db/_mirror_cards_model.py:35`)

### Prompt-Bau-Funktionen (Recall-Weaving, L3)

- **`render_cards_block(cards)`** — Recall A: gecachter, als *abgeleitet* gelabelter
  Erinnerungs-Block für den Stable-Prompt. (`runner/system_prompt.py:131`)
- **`render_search_block(cards)`** — Recall C: cue-getriggerte Treffer für den
  volatile/per-Turn-Block, trägt die session-id mit. (`runner/system_prompt.py:152`)
- **`compose(...)`** (alias `compose_system_prompts` im Runner) — webt
  `recall_cards` in stable, `recall_search` in volatile. (`runner/system_prompt.py:18`)

### Observation-Pipeline-Funktionen (Capture → Compress → Crystallize)

- **`record_observation(...)`** — Capture: pro Tool-Call eine RawObservation in
  agent-lokales JSONL. (`tools/_observations.py:89`, aufgerufen aus
  `runner/_runner_tools.py:62`)
- **`compress_session(agent_id, session_id, model)`** — Batch-Compress aller
  unkomprimierten Raws → CompressedObservations; danach Auto-Crystallize-Trigger.
  (`tools/_compress.py:88`)
- **`crystallize_session(...)`** — CompressedObservations → Crystal + Lessons via
  LLM; Lessons → Memory v2 (confidence=0.6). (`tools/_crystallize.py:84`)
- **`_save_lessons(...)`** — Lessons als Memory-Einträge `lesson.<fp>`
  (confidence 0.6, `check_contradictions=False`) bulk-schreiben.
  (`tools/_crystallize.py:51`)

### Memory-v2-Primitive (intern, re-exportiert über `_memory_store`)

- IO: `load`, `save`, `load_active`, `load_filtered`, `read_entry`, `read_key`,
  `write_key`, `write_keys_bulk`, `delete_key`, `list_keys`, `cleanup_expired`,
  `_memory_file` (`tools/_memory_io.py`, Facade `tools/_memory_store.py:9-22`)
- Logik: `MemoryEntry`, `MemoryStore`, `_migrate_entry`, `_is_expired`/`is_expired`,
  `_parse_expiry`, `_reinforce_confidence`, `_jaccard_similarity`,
  `_project_matches`, `find_contradictions`, `mark_superseded`
  (`tools/_memory_model.py`, Facade `tools/_memory_store.py:23-39`)

### UI-Komponenten (Frontend, `features/memory/`)

- **`MemoryPage.tsx`** — Seitenrahmen: Agent-Sidebar (CollapsibleSidebar) +
  Tab-Bar (memory/crystals/sessions). Lädt Agents über `agentsApi.list()`.
- **`MemoryTab.tsx`** — Memory-Browser-Tabelle: Filter-Bar (Suche `q`, `project`,
  `include_expired`), Spalten Key/Content/Confidence/Project/Updated + Delete-Button.
  `ConfidencePill` (Farbskala 80/50/<50%).
- **`CrystalsTab.tsx`** — Crystal-Liste mit aufklappbarem Detail
  (key_outcomes/lessons/files_affected + session_id).
- **`SessionsTab.tsx`** — Session-Liste, aufklappbar → lädt CompressedObservations
  lazy. `StatusPill`, `TypeBadge`, `ObservationCard` (Type/Title/Importance/
  Narrative/Facts/Files), 💎-Indikator für has_crystal.
- **`api.ts`** — `memoryApi`: `getMemory`, `deleteEntry`, `getCrystals`,
  `getSessions`, `getObservations`.
- **`types.ts`** — `MemoryEntry`, `MemoryResponse`, `Crystal`, `CrystalsResponse`,
  `MemorySession`, `MemorySessionsResponse`, `CompressedObservation`,
  `ObservationsResponse`.
- i18n-Namespace: `"memory"` (`useTranslation("memory")`).

### Scheduler / Config-Flags

- **Zahnfee-Scheduler** triggert L2-Konsolidierung nächtlich.
  (`zahnfee/scheduler.py:35-43`)
- **Agent-Flag `longterm_memory`** (bool) — schaltet Recall A/C + Datamining-Tools
  pro Agent frei. (`api/routes/_agent_schemas.py:56`, gelesen in
  `runner/runner.py:126`, `runner/system_prompt.py:39`)
- **ZahnfeeConfig**: `enabled`, `model`, `run_hour` (default 3),
  `lookback_hours` (default 24), `source_datamining`, `source_mail`, `soul`.
  (`zahnfee/config.py:35-43`)

---

## WIE

### A) Memory v2 — kuratiertes Key/Value (Schreiben)

**Trigger:** Agent ruft `write_memory(key, content, ...)`.
Flow (`tools/write_memory.py:58` → `_memory_io.py:154` → `_apply_write`):

1. `_execute` validiert: leerer Key → fail; `delete=true` → `delete_key`;
   `content` muss str sein; `confidence` muss in [0,1]; `project` explizit oder
   None (kein Kontext-Fallback, `write_memory.py:85`).
2. `write_key` lädt die ganze `memory.json` (`load`, migriert alte Schemas pro
   Eintrag via `_migrate_entry`), ruft `_apply_write` (mutiert das Dict in-place),
   schreibt zurück (`save`).
3. `_apply_write` (`_memory_io.py:96`):
   - **Contradiction Detection** (wenn `check_contradictions=True`):
     `find_contradictions(data, key, content)` läuft über alle aktiven, nicht
     abgelaufenen Einträge, berechnet **Jaccard-Similarity** (Token-Set,
     Stopwörter len≤2 gefiltert) zwischen neuem Content und jedem Bestand; bei
     `sim >= 0.7` (`_CONTRADICTION_THRESHOLD`) wird der Key Kandidat. Diese werden
     via `mark_superseded` als `is_latest=False` markiert (mit `superseded_by`,
     `superseded_at`).
   - **Reinforcement** (Key existiert schon): Content überschrieben, `updated_at`/
     `last_reinforced_at`=now, `confidence = old + 0.1*(1-old)` (konvergiert
     gegen 1.0, `_reinforce_confidence`), `reinforcements += 1`, `is_latest=True`,
     `supersedes` erweitert; `expires_at`/`project` nur bei explizitem Wert.
   - **Neu**: Vollschema, `confidence` = übergeben oder 0.5 (geclamped),
     `reinforcements=0`, `supersedes` = die gekippten Keys.
   - **Expiry-Parsing** (`_parse_expiry`): `+Nh/+Nd/+Nw/+Nm` (m≈30d) → ISO-Timestamp;
     sonst Wert unverändert.
4. Rückgabe an Agent: Bestätigung + `confidence`, `reinforcements`, ggf.
   `project`, `expires_at`, und bei Widersprüchen `superseded`-Liste + Warning.

**Bulk:** `write_keys_bulk` macht N Einträge mit **einem** File-Read+Write
(`_apply_write` pro Eintrag, dann ein `save`). Genutzt von `_save_lessons`.

### B) Memory v2 — Lesen / Suche

- **`read_memory` ohne key** → `list_keys(agent_id, filter_project, active_project)`:
  alle Keys, die nicht expired, `is_latest=True`, und `_project_matches`.
- **`read_memory` mit key** → `read_entry`: voller Eintrag, kein Projekt-Filter
  (expliziter Lookup ignoriert Projekt-Grenzen), aber expired → None.
- **`search_memory`** → `load_filtered(...)` (expired-, superseded-, Projekt-Filter
  in einem), dann regex/substring über Key + Content. Snippet rund um den ersten
  Content-Match (oder Key-Prefix). `match_score = #content_matches + (2 wenn
  Key-Match)`, sortiert nach `match_score × confidence`, dann `_sort_score`
  entfernt. (`search_memory.py:59-145`)
- **Projekt-Sichtbarkeit** (`_project_matches`, `_memory_model.py:107`):
  `filter_project='*'` → alles; `filter_project=X` → project=X **oder** None
  (global); sonst `active_project` aus Session-Kontext; ohne Kontext → nur globale.

### C) Observation-Pipeline (Capture → Compress → Crystallize)

1. **Capture** (`runner/_runner_tools.py:62`): nach jedem ausgeführten Tool-Call
   ruft der Runner `record_observation(agent_id, session_id, tool_name, tool_input,
   tool_output, hook_type=POST_TOOL_USE|POST_TOOL_FAILURE)`. User-Ablehnungen
   (Tool-Confirm „nein") erzeugen **keine** Observation. RawObservation → JSONL
   `agents/<id>/observations/<sid>.jsonl`.
2. **Session-Ende** (`runner/runner.py:264`): wenn der Agent fertig ist (keine
   tool_uses) → `session_end(status="completed")`, danach fire-and-forget
   `_safe_compress` (in `errors_log.capture` gewrappt, blockt `Done` nicht).
3. **Compress** (`tools/_compress.py:88`): lädt alle noch unkomprimierten Raws,
   batcht à `COMPRESS_BATCH_SIZE` (30) in LLM-Calls (`COMPRESS_SYSTEM`, temp 0.0,
   `max_tokens = min(8192, N*220+256)`), schreibt CompressedObservations
   (`agents/<id>/compressed/<sid>.jsonl`), markiert Raws bulk als compressed. Bei
   LLM-Fehler → `fallback_compressed` pro Raw.
4. **Auto-Crystallize** (`tools/_compress.py:115`): nach dem Compress, wenn
   `len(load_compressed) >= MIN_OBSERVATIONS` (5), wird ein Background-Task
   `crystallize_session` gestartet (in `errors_log.capture`).
5. **Crystallize** (`tools/_crystallize.py:84`): lädt CompressedObservations,
   baut Chain-Text, ruft LLM (`CRYSTALLIZE_SYSTEM`, temp 0.0, max 1024) → Crystal
   (narrative/key_outcomes/files_affected/lessons). Bei Fehler →
   `fallback_digest`. Files dedupliziert aus Observations + LLM. Speichert Crystal
   **append-only** in `crystals.jsonl`. Lessons → Memory v2 via `_save_lessons`
   (confidence 0.6, `lesson.<fingerprint>`-Keys, **ohne** Contradiction-Check).
   `force=False` skippt, wenn schon kristallisiert oder < 5 Observations.

> Wichtig: **`crystallize_session` ist agent-lokal** — es liest die
> agent-eigenen CompressedObservations. Für externe/importierte Mirror-Sessions
> (z.B. andere Claude-Instanzen) gibt es diese nicht → die Card-Konsolidierung
> (Schicht 3) nutzt deshalb **nicht** `crystallize_session`, sondern die
> Mirror-Events direkt (siehe D).

### D) Proaktiver Recall — L2 Konsolidierung (Schlaf-Batch)

**Trigger:** Zahnfee-Scheduler (`zahnfee/scheduler.py`). Der Loop wacht jede Minute
auf; einmal pro Tag bei `now.hour == cfg.run_hour` (default 3 UTC) startet er den
Zahnfee-Runner UND — wenn `cfg.model` gesetzt — einen Background-Task
`consolidate_recent(cfg.lookback_hours, cfg.model)`.

Flow `consolidate_recent` (`cards/consolidate.py:121`):

1. `list_sessions(from_date = now - lookback_hours, limit=200)` aus dem
   **Mirror** (`db/_mirror_sessions.list_sessions`, aggregiert die `events`-Tabelle
   per `GROUP BY session_id`).
2. Pro Session `consolidate_session(sid, model)`:
   - `get_session_detail(session_id)` → meta + gemergte Events (`_merge_chunks`
     fasst Chunk-/Block-Fragmente zusammen). Fehlt → None.
   - `_llm_tags(events, model)` → **ein** LLM-Call mit `CARD_SYSTEM` (Archivar-
     Prompt: „summarize, do NOT continue/reply"). **Claude-Sonderweg**: erst MIT
     Assistant-Prefill `{` (erzwingt JSON-Output), bei BadRequest nochmal OHNE
     Prefill — statt lautlos leer. `parse_card_response` zieht das JSON-Objekt mit
     `gist`-Key (überspringt vorangestellten echoed Content via `_iter_json_objects`,
     String-/Escape-aware Klammer-Balancierung).
   - Kein Gist? → **ein Retry** gegen Modell-Varianz. Immer noch kein Gist? → Card
     wird **NICHT** gespeichert (retry-fähig, nicht lautlos leer), `None`.
   - `event_type_counts(session_id)` → `derive_groundedness(tool_result,
     assistant_text)` (observed wenn obs≥2·clm, claimed wenn clm≥2·obs, sonst mixed).
   - **Embedding**: nur wenn `embed_model` konfiguriert; `aembed(gist, model,
     embed_type="db")`. Fehler → Card trotzdem ohne Embedding.
   - `Card`-Objekt bauen (`card_id="card:{session_id}"`, created_at = Session-Zeit),
     `upsert_card(card, embedding)` → idempotent ON CONFLICT card_id;
     `computed_at = now()` serverseitig (getrennt von created_at).

### E) Proaktiver Recall — L3 Weaving (Recall A + C)

**Trigger:** jeder `runner.run(...)`, NUR wenn `agent.longterm_memory` true
(`runner/runner.py:121-136`). Best-effort in try/except.

- **Recall A** (`top_cards_for(agent["id"], limit=8)`): Top-N Cards nach
  `ORDER BY (salience='high') DESC, created_at DESC NULLS LAST`. Einmal pro
  Session geladen, in den **stable** (gecachten) System-Prompt gewoben
  (`render_cards_block`). Ändert sich nur bei nächtlicher Konsolidierung → innerhalb
  der Session cache-stabil (Anthropic prüft den ganzen System-Block byteweise).
- **Recall C** (`search_cards(_ut, limit=3)`): nur wenn die User-Eingabe ≥3 Wörter
  hat (`_user_text` zieht Text aus str/Content-Block-Liste). pgvector-Cosine-Suche
  über `cards.embedding` (`embed_type="query"`). Treffer landen im **volatile**
  Block (`render_search_block`), tragen die session-id mit (für tieferes Graben via
  `datamining_*`).
- Beide Blöcke sind klar als „automatisch verdichtet / abgeleitet" gelabelt —
  NICHT als kuratiertes Memory.
- Zusätzlich injiziert `_inject_longterm_memory` (bei `longterm_memory=True`) die
  Datamining-Tools (`datamining_search/today/timeline` + `_semantic` wenn
  embed_model) in `tool_schemas`/`allowed_tools` + einen Hinweis-Text.

### Zustands-/Lifecycle-Notizen

- Memory-Eintrag-Lifecycle: neu → reinforced (n-mal) → superseded (is_latest=False,
  bleibt als History) → expired (von `cleanup_expired` gelöscht). Superseded bleibt;
  nur Expired wird hart gelöscht.
- Session-Status (`tools/_sessions.py`): active → completed | abandoned | paused.
  paused = max_iterations (resumable), abandoned = echter Error.
- Card-Lifecycle: rein abgeleitet, jederzeit `wipe_cards()` + rebuild aus Events.
  `card_id` deterministisch aus session_id → upsert idempotent.

---

## WO

### cards/ (Konsolidierung L2 + Prompts)

- `cards/__init__.py:1` — Modul-Doc (Proaktiver Recall, L2 Card-Writer).
- `cards/consolidate.py:24` — `_is_claude(model)` (Prefix-Strip).
- `cards/consolidate.py:29` — `_llm_tags(events, model)` (LLM-Call + Prefill-Logik).
- `cards/consolidate.py:62` — `consolidate_session(session_id, model) -> Card|None`.
- `cards/consolidate.py:73-80` — Gist-Retry-Gate + „nicht lautlos leer speichern".
- `cards/consolidate.py:82-85` — groundedness via `event_type_counts`.
- `cards/consolidate.py:87-95` — Embedding (nur bei embed_model, Fehler tolerant).
- `cards/consolidate.py:98-113` — Card-Bau + `upsert_card`.
- `cards/consolidate.py:121` — `consolidate_recent(lookback_hours, model, limit=200)`.
- `cards/_consolidate_prompts.py:20` — `DEFAULT_CHAR_BUDGET = 24000`.
- `cards/_consolidate_prompts.py:22` — `CARD_SYSTEM` (Archivar-Prompt).
- `cards/_consolidate_prompts.py:45` — `format_session_text(events, char_budget)` (head+tail-Truncation).
- `cards/_consolidate_prompts.py:65` — `card_user_message(events, char_budget)` (Transkript-Delimiter).
- `cards/_consolidate_prompts.py:77` — `_iter_json_objects(text)` (balanciertes {…} yield).
- `cards/_consolidate_prompts.py:116` — `parse_card_response(text) -> dict` (gist-Key-Wahl, Enum-Validierung, topics≤6, gist≤300).

### db/ (Card-Store + Mirror)

- `db/_mirror_cards_model.py:12` — `@dataclass Card` (Vertrag, alle Felder).
- `db/_mirror_cards_model.py:6-9` — `VALENCE`, `SALIENCE`, `GROUNDEDNESS`, `CARD_SCHEMA_VERSION=1`.
- `db/_mirror_cards_model.py:35` — `derive_groundedness(tool_result_count, assistant_text_count)`.
- `db/_mirror_cards.py:16-28` — `_COLS` (Insert) / `_READ_COLS` (ohne Embedding).
- `db/_mirror_cards.py:31` — `_vec_str(embedding)` (pgvector-Literal).
- `db/_mirror_cards.py:40` — `_JSONB_FIELDS` (topics/source/superseded_by/supersedes).
- `db/_mirror_cards.py:52` — `upsert_card(card, embedding)` (ON CONFLICT card_id; `computed_at=now()`).
- `db/_mirror_cards.py:111` — `get_card(card_id)`.
- `db/_mirror_cards.py:126` — `wipe_cards()`.
- `db/_mirror_cards.py:142` — `top_cards_for(agent_id, limit=8)` (Recall A, ORDER BY salience/created_at).
- `db/_mirror_cards.py:167` — `search_cards(query, limit=5)` (Recall C, pgvector cosine `<=>`).
- `db/_mirror_sessions.py:12` — `list_sessions(...)` (events-Aggregat).
- `db/_mirror_sessions.py:62` — `event_type_counts(session_id)`.
- `db/_mirror_sessions.py:82` — `get_session_detail(session_id)`.
- `db/_mirror_sessions.py:126` — `_merge_chunks(rows)` / `:159` `_finalize(buf)`.
- `db/_mirror_ddl.py:133-152` — `CREATE TABLE cards` (DDL).
- `db/_mirror_ddl.py:153-155` — Card-Indexes (`cards_session`, `cards_agent`, `cards_recency_salience`).
- `db/_mirror_ddl.py:207` — `ensure_embed_col(conn, table)` (embedding-Spalte, events|cards).
- `db/mirror.py:62-76` — Init: DDL_TABLES + `ensure_embed_col(cards)`.
- `db/mirror.py:102-112` — `on_embed_model_change` (Spalte anpassen + Backfill für events+cards).
- `db/_mirror_embed.py:30` — `embed_text(e)`; `:41` `embed_event`; `:79` `backfill_loop` (events).
- `db/_mirror_search.py:11` — `_dt(s)`; `:22` `_pool()`; `:67` `search_events`; `:121` `_semantic_search`.

### tools/ (Memory v2 + Observation-Pipeline)

- `tools/read_memory.py:33` — `_execute`; `:73` `TOOL`.
- `tools/write_memory.py:58` — `_execute`; `:118` `TOOL`.
- `tools/search_memory.py:59` — `_execute`; `:148` `TOOL`.
- `tools/_memory_store.py:9-39` — Facade-Re-Exports (`__all__` ab `:41`).
- `tools/_memory_io.py:23` — `_memory_file(agent_id)` (`agents/<id>/memory.json`).
- `tools/_memory_io.py:27` `load`; `:41` `save`; `:56` `load_filtered`; `:77` `read_entry`;
  `:96` `_apply_write`; `:154` `write_key`; `:182` `write_keys_bulk`; `:212` `delete_key`;
  `:221` `list_keys`; `:236` `cleanup_expired`.
- `tools/_memory_model.py:16-18` — Konstanten (`_CONFIDENCE_DEFAULT=0.5`, `_CONFIDENCE_STEP=0.1`, `_CONTRADICTION_THRESHOLD=0.7`).
- `tools/_memory_model.py:25` `_migrate_entry`; `:71` `_parse_expiry`; `:89` `_reinforce_confidence`;
  `:94` `_jaccard_similarity`; `:107` `_project_matches`; `:131` `find_contradictions`; `:151` `mark_superseded`.
- `tools/_compress.py:88` — `compress_session`; `:42` `_compress_batch`; `:115-136` Auto-Crystallize-Trigger.
- `tools/_crystallize.py:38` — `MIN_OBSERVATIONS=5`; `:51` `_save_lessons`; `:84` `crystallize_session`.
- `tools/_crystallize_storage.py:17-19` — `_crystals_file` (`agents/<id>/crystals.jsonl`); `:22` `save_crystal`; `:49` `list_crystals`; `:80` `get_crystal`.
- `tools/_compress_storage.py:16` — `_compressed_file` (`agents/<id>/compressed/<sid>.jsonl`).
- `tools/_observations.py:36` — `_obs_file` (`agents/<id>/observations/<sid>.jsonl`); `:89` `record_observation`; `:126` `list_raw_observations`; `:190` `mark_compressed_bulk`.
- `tools/_sessions.py:30` — `_sessions_dir` (`agents/<id>/sessions/`); `:59` `session_start`; `:92` `session_end`; `:134` `session_list`.

### runner/ (Capture-Hook + Recall-Weaving)

- `runner/runner.py:49` — `_user_text(ui)` (Recall-C-Cue).
- `runner/runner.py:121-136` — Recall A+C laden (`top_cards_for` / `search_cards`).
- `runner/runner.py:153-164` — `compose_system_prompts(...recall_cards, recall_search)`.
- `runner/runner.py:264-278` — Session-Ende → `_safe_compress` (fire-and-forget).
- `runner/runner.py:32` — `from ...system_prompt import compose as compose_system_prompts`.
- `runner/_runner_tools.py:62` — `record_observation(...)` nach Tool-Execution.
- `runner/system_prompt.py:18` — `compose(...)`; `:105` `_inject_longterm_memory`;
  `:131` `render_cards_block`; `:152` `render_search_block`.
- `runner/system_prompt.py:90-95` — `_LONGTERM_MEMORY_HINT`.

### zahnfee/ (Scheduler-Trigger)

- `zahnfee/scheduler.py:35-43` — L2-Trigger (`consolidate_recent`).
- `zahnfee/config.py:35-43` — `ZahnfeeConfig` (`model`, `run_hour`, `lookback_hours`).

### api/

- `api/routes/agent_memory.py:21` — Router; `:24` `_get_agent_or_404`;
  `:35` GET memory; `:96` `_project_matches_simple`; `:107` DELETE; `:125` crystals;
  `:165` memory-sessions; `:212` observations.
- `api/routes/_agent_schemas.py:56` — `longterm_memory: bool | None`.
- `api/main.py:13`,`:106` — Router-Import + `include_router`.

### llm/ (Embedding für Cards/Search)

- `llm/embed.py:81` — `dim_for_model(model)`; `:104` `aembed(text, model, embed_type)`;
  `:115` `aembed_batch`; `:83-88` `_BY_MODEL` (EMBED_MODELS → dim/litellm).
- `llm/client.py:38` — `_strip_provider_prefix` (von consolidate `_is_claude` genutzt).

### frontend/src/features/memory/

- `MemoryPage.tsx:14` — `MemoryPage` (Tabs memory/crystals/sessions).
- `MemoryTab.tsx:13` — `MemoryTab`; `:169` `ConfidencePill`.
- `CrystalsTab.tsx:13` — `CrystalsTab`; `:127` `Section`.
- `SessionsTab.tsx:13` — `SessionsTab`; `:115` `ObservationCard`; `:147` `StatusPill`; `:161` `TypeBadge`.
- `api.ts:7` — `memoryApi`.
- `types.ts:1-73` — alle Memory-View-Typen.

### tests/

- `core/tests/test_consolidate.py` — Card-Parsing/Format/Truncation/Build-Tests
  (pure, ohne PG). Invarianten siehe „Offene Enden".

---

## WARUM

### Drei getrennte Stores — und warum die Trennung heilig ist

- **Kuratiertes Memory v2** (`memory.json`, agent-geschrieben) und **abgeleitete
  Cards** (PostgreSQL, recompute-safe) sind absichtlich getrennte Backends. Grund
  (Design-Doc, joshuas Befund #3): ein `wipe-and-rebuild` der abgeleiteten Schicht
  darf die handgeschriebenen Agent-Notizen NICHT mitreißen. `wipe_cards()` rührt nur
  die `cards`-Tabelle an. Im Prompt werden Card-Blöcke **klar als „abgeleitet/
  automatisch verdichtet" gelabelt** — nie als kuratiertes Memory. Wer die Stores
  vermischt, bricht genau diese Garantie.
- **Observation-Pipeline → Crystals → Lessons → Memory v2** ist der EINE Pfad, über
  den abgeleitetes Wissen wieder ins kuratierte Memory zurückfließt — und zwar als
  `lesson.<fp>`-Keys mit **`check_contradictions=False`** (`_crystallize.py:72`),
  damit batch-geschriebene Lessons sich nicht gegenseitig als Widersprüche kippen.

### Cache-Ökonomie ist der Existenzgrund der Recall-Architektur

- Recall A wird in den **stable** (gecachten) System-Prompt gewoben und nur **einmal
  pro Session** geladen → ab Turn 2 Cache-Read, fast gratis. Wer in den stable-Block
  etwas Volatiles schreibt (Uhrzeit etc.), bricht den Anthropic-Cache (Issue #141 —
  deshalb `_volatile_section` nur Datum, keine Uhrzeit). Recall C steht bewusst im
  **volatile** Block (ändert sich per Turn, darf den stable-Cache nicht anfassen).
- Recall C feuert NUR bei ≥3 Wörtern Eingabe (`runner.py:133`) — „kein Token-Brand
  bei `test`/Einzelwörtern". Das teure Denken (LLM-Konsolidierung) passiert
  **offline im Schlaf** (Zahnfee-Batch, billiges Modell); der Recall tagsüber holt
  nur fertige Karten. Das ist das „Token-Prinzip" aus dem Design-Doc.

### Konsolidierung nutzt Mirror-Events, NICHT crystallize_session

- Eine subtile, verifizierte Falle: `crystallize_session(agent_id, session_id)` liest
  **agent-lokale** CompressedObservations. Für die meisten Mirror-Sessions (externe
  Instanzen, Importe, andere Agents) existieren diese nicht → es gäbe keine Card.
  Deshalb verdichtet `consolidate_session` die **Mirror-Events**
  (`get_session_detail`) und reused nur die crystallize-**Prompt-Maschinerie**
  (`call_with_tools` + Card-Prompt + Parse). Wer das auf `crystallize_session`
  umbaut, verliert stillschweigend alle Cards für nicht-lokale Sessions.

### Embedding-Dimension MUSS dynamisch + gleich sein

- `cards.embedding` und `events.embedding` teilen sich denselben pgvector-Raum und
  dieselbe `embed_model`-Quelle (`ensure_embed_col(table="cards")` nutzt
  `dim_for_model(load_config().embed_model)`). Hartkodierte Dimension (z.B.
  vector(4096)) bricht den gemeinsamen Index. Bei Modellwechsel droppt
  `ensure_embed_col` die Spalte und legt sie neu an — Cards verlieren dann ihre
  Embeddings, bis re-konsolidiert wird. `consolidate_session` nutzt `embed_type="db"`,
  `search_cards` `embed_type="query"` — die Asymmetrie ist Absicht (viele Embedding-
  Provider wollen unterschiedliche Prefixe für Dokument vs. Query).

### Stille Fehler werden bewusst vermieden

- `_llm_tags` versucht bei Claude **erst mit, dann ohne** Prefill statt lautlos leer
  zurückzugeben (`consolidate.py:42-59`). `consolidate_session` retried den Gist
  einmal und speichert bei Misserfolg **keine** Card (retry-fähig) statt eine leere
  (`consolidate.py:73-80`). Beide Card-Background-Tasks (compress→crystallize,
  zahnfee→consolidate) laufen in `errors_log.capture(reraise=False)` bzw. try/except
  — ein Crash im Nacht-Batch killt nicht den Server, taucht aber im errors_log auf.

### Invarianten / Annahmen

- **`card_id = "card:{session_id}"`** ist die Idempotenz-Invariante: ein
  Re-Consolidate derselben Session überschreibt genau eine Zeile (ON CONFLICT).
- **`computed_at` (Card-Berechnungszeit) ≠ `created_at` (Session-Zeit)**: das
  recency-Ranking in Recall A nutzt `created_at`, nicht `computed_at` — sonst wären
  alle nächtlich neu gerechneten Cards „frisch" und das Ranking wertlos.
- **`is_latest`/`superseded_*`** sind Memory-v2-Felder, die auf Cards als Felder
  existieren (`confidence`, `supersedes`, `superseded_by`) aber in v1 **ungenutzt**
  sind — sie sind v2-ready (Verify-/Contradiction-Reasoning), nicht tot.
- **`longterm_memory` ist der Master-Schalter**: ohne das Agent-Flag kein Recall A/C
  und keine Datamining-Tools. Cards werden trotzdem konsolidiert (Zahnfee ist
  agent-unabhängig), aber nicht gewoben.
- **PG-Pool fehlt → alles degradiert lautlos**: `_pool()` None → `top_cards_for`/
  `search_cards`/`upsert_card` geben leer/no-op zurück. Recall ist best-effort; ohne
  Mirror-DB funktioniert HH2 weiter, nur ohne proaktives Gedächtnis.

### Was bricht, wenn man X anfasst

- `CARD_SYSTEM`-Prompt ändern → `parse_card_response`-Erwartungen + `test_consolidate`
  brechen; Modell könnte die Session fortführen statt zusammenfassen.
- `_CONTRADICTION_THRESHOLD` (0.7) senken → mehr False-Positive-Supersessions
  (legitime Notizen werden fälschlich als veraltet markiert). Erhöhen → Widersprüche
  bleiben unentdeckt.
- `MIN_OBSERVATIONS` (5) ändern → Häufigkeit der Auto-Crystallize-Tasks.
- `_READ_COLS` vs `_COLS`: Embedding wird beim Lesen bewusst NICHT geladen (großer
  Vektor). Wer Embedding in `_READ_COLS` aufnimmt, bläht jede Recall-Query auf.

---

## Datenmodell

### Tabelle `cards` (PostgreSQL/Mirror, `db/_mirror_ddl.py:133`)

| Spalte | Typ | Bedeutung |
|---|---|---|
| `card_id` | TEXT PK | `"card:{session_id}"`, deterministisch |
| `session_id` | TEXT NOT NULL | Anker im immutablen Datamining |
| `gist` | TEXT | 1–3 Zeilen Kern (≤300 Zeichen) |
| `valence` | TEXT | good\|bad\|neutral |
| `salience` | TEXT | high\|low |
| `groundedness` | TEXT | observed\|claimed\|mixed (v1: Event-Typ-Heuristik) |
| `topics` | JSONB | ≤6 Cue-Wörter (Recall-C-Trigger) |
| `agent_id` / `agent_name` / `username` | TEXT | Provenance |
| `created_at` | TIMESTAMPTZ | **Session-Zeit** → Recency-Ranking |
| `source` | JSONB | `{session_id, event_count}` (lazy reconstruction) |
| `confidence` | REAL DEFAULT 1.0 | v2, ungenutzt in v1 |
| `superseded_by` / `supersedes` | JSONB | v2, ungenutzt in v1 |
| `schema_version` | INTEGER DEFAULT 1 | recompute-safety |
| `computed_at` | TIMESTAMPTZ | wann die Ableitung lief (`now()` server) |
| `consolidation_model` | TEXT | welches Modell die Card schrieb |
| `embedding` | vector(dim) | dynamisch via `ensure_embed_col`, Mirror-Dim |
| `embedding_model` / `embedded_at` | TEXT / TIMESTAMPTZ | Embedding-Provenance |

Indexes: `cards_session(session_id)`, `cards_agent(agent_id, created_at)`,
`cards_recency_salience(created_at DESC, salience)`.

### `memory.json` (pro Agent, `agents/<id>/memory.json`) — Dict key → MemoryEntry

`MemoryEntry`-Felder (`_memory_model.py:25` / `_memory_io.py:137`):
`content`, `created_at`, `updated_at`, `expires_at`, `confidence` (0.5 default),
`reinforcements` (int), `last_reinforced_at`, `is_latest` (bool),
`superseded_by`, `superseded_at`, `supersedes` (list), `project` (None=global).
Konstanten: `_CONFIDENCE_DEFAULT=0.5`, `_CONFIDENCE_STEP=0.1`,
`_CONTRADICTION_THRESHOLD=0.7`.

### Observation-Pipeline-Dateien (pro Agent, JSONL)

- `agents/<id>/observations/<sid>.jsonl` — RawObservation (Capture pro Tool-Call).
- `agents/<id>/compressed/<sid>.jsonl` — CompressedObservation
  (id/session_id/agent_id/raw_observation_id/timestamp/type/title/facts/concepts/
  files/importance/narrative).
- `agents/<id>/crystals.jsonl` — Crystal append-only (id/session_id/agent_id/project/
  created_at/narrative/key_outcomes/files_affected/lessons/source_observation_ids/
  observation_count).
- `agents/<id>/sessions/<sid>.json` — Session (id/agent_id/project/started_at/
  ended_at/status/observation_count/model/first_prompt/summary).

### Mirror-Tabellen (gelesen, hier nicht definiert)

- `events` — Roh-Events (Capture L1, Hook→Datamining). Quelle für `list_sessions`,
  `get_session_detail`, `event_type_counts`, `backfill_loop`.
- `sessions` — Mirror-Session-Metadaten (von `get_session_detail` bevorzugt, mit
  events-Fallback).

### Config / Env

- **ZahnfeeConfig** (`HH_CONFIG_DIR/zahnfee.json`): `enabled` (bool),
  `model` (str — leer → keine Konsolidierung), `run_hour` (int, default 3 UTC),
  `lookback_hours` (int, default 24), `source_datamining`, `source_mail`, `soul`.
- **LLM-Config** (`load_config()`): `embed_model` (steuert Card-Embedding +
  pgvector-Dim + `datamining_semantic`-Verfügbarkeit).
- **Agent-Config**: `longterm_memory` (bool — Master-Schalter Recall A/C +
  Datamining-Tools), `llm_model` (Default-Compress/Crystallize-Modell).
- Mirror-DSN (für `_pool()`) — ohne → Recall/Cards no-op.

### Events / Trigger

- `session_end(completed)` → `compress_session` (fire-and-forget).
- `compress_session` → Auto-`crystallize_session` (wenn ≥5 CompressedObservations).
- Zahnfee-Tages-Tick (`run_hour`) → `consolidate_recent`.
- `runner.run` (mit `longterm_memory`) → `top_cards_for` (A) + ggf. `search_cards` (C).
- `on_embed_model_change` → `ensure_embed_col(events+cards)` + Backfill.

---

## Offene Enden

### v2 bewusst ungebaut (kein Bug, sondern Scope-Bremse)

- **Kein Contradiction-Reasoning / Umklassifizieren auf Cards.** `groundedness` ist
  nur die billige Event-Typ-Heuristik (`derive_groundedness`), kein echtes Reasoning.
  (`cards/consolidate.py:5-6`, Design-Doc v2.)
- **Kein Verify-before-trust-Gate.** Niedrig-Confidence-Cards werden beim Recall
  NICHT markiert/blockiert. Die Felder `confidence`, `superseded_by`, `supersedes`
  auf `Card` sind vorhanden aber UNGENUTZT (v2-ready). (`_mirror_cards_model.py:27-29`.)
- **Keine Modell-Eskalation** in der Konsolidierung (immer `cfg.model`, billig).

### Tote / inkonsistente Teile

- **`load_active`** (`_memory_io.py:47`) ist nur ein Alias für `load_filtered` „für
  Abwärtskompatibilität" — Kandidat fürs Aufräumen, prüfen ob noch Aufrufer existieren.
- **Frontend `StatusPill` (`SessionsTab.tsx:147`)** kennt Status `active/closed/
  crystallized`. Das Backend liefert aber `active/completed/abandoned/paused`
  (`_sessions.py:16-23`) — `completed/abandoned/paused` fallen alle in den grauen
  Default-Stil, `closed`/`crystallized` werden nie getroffen. UI/Backend-Status-Drift.
- **`session_list` Known Limitation** (`_sessions.py:145-147`): `glob()` lädt ALLE
  Session-Dateien vor dem `limit`-Cut; bei 10k+ Sessions linearer Speicher. Für
  aktuellen Scope (<1000) ok, aber dokumentierte Schuld.
- **`get_agent_memory` umgeht `load_filtered`** und nutzt `load()` + eigenes
  `_project_matches_simple` (`agent_memory.py:53,96`), weil der Browser ALLE
  Einträge zeigen will (nicht die Agent-„ohne aktives Projekt nur globale"-Semantik).
  Zwei verschiedene Projekt-Filter-Pfade — bewusst, aber Doppelpflege-Risiko.
- **`embed_text`/`embed_event` in `_mirror_embed.py`** sind die EVENT-Embedding-
  Pipeline; Cards embedden separat in `consolidate_session` direkt über `aembed`.
  Zwei Embedding-Aufruf-Pfade, gleiche `embed_model`-Quelle.

### Annahmen, die kippen können

- **Recall A lädt einmal pro Session** und cached für die ganze Session. Wird die
  Session sehr lang und mitten drin nachts konsolidiert, sieht der Agent die neuen
  Cards erst in der nächsten Session — by design (Cache-Stabilität), aber ein
  „warum sieht der Agent das nicht?"-Stolperstein.
- **Zahnfee läuft UTC** (`datetime.now(timezone.utc)`, `run_hour` default 3) — die
  „nächtliche" Konsolidierung ist 3 Uhr UTC, nicht lokal.
- **`consolidate_recent` Default `limit=200`**: bei mehr als 200 Sessions im
  Lookback-Fenster werden ältere nicht konsolidiert. Kein Paging/Cursor.

### Verifizierte Test-Invarianten (`core/tests/test_consolidate.py`)

- `parse_card_response` wählt das gist-Key-Objekt, validiert Enums (ungültig →
  neutral/low), cappt topics auf 6, gibt bei Müll den Fallback `{gist:"",...}` zurück,
  strippt Code-Fences. (`test_consolidate.py:14-37`)
- `format_session_text` truncatet große Sessions auf head+tail mit „chars elided"-
  Marker (Ergebnis < budget+Marker). (`test_consolidate.py:56-61`)
- `consolidate_session` baut die Card korrekt (card_id, groundedness=observed bei
  10 tool_result vs 2 assistant_text, embedding None wenn embed_model leer), gibt
  None bei fehlender Session. (`test_consolidate.py:66-110`)

### Referenz-Docs

- `docs/superpowers/specs/2026-05-29-proactive-recall-design.md` (Design, v1/v2-Schnitt,
  „grüner Elefant", schmied=Capture/joshua=L2/L3-Aufteilung).
- `docs/superpowers/plans/2026-05-29-proactive-recall.md` (Plan/Tasks).
- `docs/superpowers/plans/2026-05-29-datamining-live-ingest.md` (Capture L1 / externe Instanzen).
