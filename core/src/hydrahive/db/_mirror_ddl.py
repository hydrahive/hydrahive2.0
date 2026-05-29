"""Mirror — Schema-DDL und Embedding-Spalten-Management."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


DDL_TABLES = """
CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,
  username    TEXT,
  agent_id    TEXT,
  agent_name  TEXT,
  project_id  TEXT,
  title       TEXT,
  status      TEXT,
  started_at  TIMESTAMPTZ,
  updated_at  TIMESTAMPTZ,
  mirrored_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS events (
  id              TEXT PRIMARY KEY,
  message_id      TEXT NOT NULL,
  session_id      TEXT NOT NULL,
  block_index     INTEGER NOT NULL,
  chunk_index     INTEGER NOT NULL DEFAULT 0,
  chunk_total     INTEGER NOT NULL DEFAULT 1,
  username        TEXT,
  agent_id        TEXT,
  agent_name      TEXT,
  project_id      TEXT,
  event_type      TEXT NOT NULL,
  text            TEXT,
  tool_name       TEXT,
  tool_use_id     TEXT,
  tool_input      JSONB,
  tool_output     TEXT,
  is_error        BOOLEAN,
  token_count     INTEGER,
  created_at      TIMESTAMPTZ NOT NULL,
  mirrored_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_session ON events (session_id);
CREATE INDEX IF NOT EXISTS events_message ON events (message_id, block_index, chunk_index);
CREATE INDEX IF NOT EXISTS events_user    ON events (username, created_at);
CREATE INDEX IF NOT EXISTS events_type   ON events (event_type, created_at);
CREATE INDEX IF NOT EXISTS events_tool   ON events (tool_name) WHERE tool_name IS NOT NULL;
CREATE TABLE IF NOT EXISTS llm_calls (
  id                      TEXT PRIMARY KEY,
  session_id              TEXT NOT NULL,
  created_at              TIMESTAMPTZ NOT NULL,
  agent_id                TEXT,
  user_id                 TEXT,
  provider                TEXT NOT NULL,
  model                   TEXT NOT NULL,
  temperature             REAL,
  max_tokens              INTEGER,
  reasoning_effort        TEXT,
  prompt_tokens           INTEGER,
  completion_tokens       INTEGER,
  cache_read_tokens       INTEGER,
  cache_creation_tokens   INTEGER,
  stop_reason             TEXT,
  ttft_ms                 INTEGER,
  total_ms                INTEGER,
  cost_micros             BIGINT,
  turn_in_session         INTEGER,
  mirrored_at             TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS llm_calls_session ON llm_calls (session_id);
CREATE INDEX IF NOT EXISTS llm_calls_created ON llm_calls (created_at);
CREATE INDEX IF NOT EXISTS llm_calls_agent   ON llm_calls (agent_id, created_at);
CREATE INDEX IF NOT EXISTS llm_calls_user    ON llm_calls (user_id, created_at);
CREATE INDEX IF NOT EXISTS llm_calls_model   ON llm_calls (model, created_at);
CREATE TABLE IF NOT EXISTS compaction_events (
  id                          TEXT PRIMARY KEY,
  session_id                  TEXT NOT NULL,
  created_at                  TIMESTAMPTZ NOT NULL,
  agent_id                    TEXT,
  user_id                     TEXT,
  triggered_by                TEXT,
  trigger_threshold_pct       INTEGER,
  model                       TEXT,
  source                      TEXT,
  instructions                TEXT,
  tool_result_limit           INTEGER,
  skipped                     BOOLEAN NOT NULL DEFAULT false,
  skip_reason                 TEXT,
  skip_reason_params          JSONB,
  messages_total              INTEGER,
  messages_visible_before     INTEGER,
  messages_to_summarize       INTEGER,
  messages_kept               INTEGER,
  tokens_before               INTEGER,
  tokens_after_estimate       INTEGER,
  cut_kept_from_index         INTEGER,
  cut_is_split_turn           BOOLEAN,
  cut_turn_prefix_count       INTEGER,
  summary_chars               INTEGER,
  summary_tokens_estimate     INTEGER,
  facts_count                 INTEGER,
  files_extracted_count       INTEGER,
  compaction_message_id       TEXT,
  had_previous_summary        BOOLEAN,
  duration_ms                 INTEGER,
  error                       TEXT,
  mirrored_at                 TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS compaction_events_session ON compaction_events (session_id);
CREATE INDEX IF NOT EXISTS compaction_events_created ON compaction_events (created_at);
CREATE INDEX IF NOT EXISTS compaction_events_agent   ON compaction_events (agent_id, created_at);
CREATE INDEX IF NOT EXISTS compaction_events_skipped ON compaction_events (skipped) WHERE skipped = true;
CREATE TABLE IF NOT EXISTS errors_log (
  id              TEXT PRIMARY KEY,
  created_at      TIMESTAMPTZ NOT NULL,
  session_id      TEXT,
  agent_id        TEXT,
  user_id         TEXT,
  source          TEXT NOT NULL,
  severity        TEXT NOT NULL DEFAULT 'error',
  error_type      TEXT,
  error_message   TEXT,
  traceback       TEXT,
  context         JSONB,
  mirrored_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS errors_log_session  ON errors_log (session_id);
CREATE INDEX IF NOT EXISTS errors_log_source   ON errors_log (source, created_at);
CREATE INDEX IF NOT EXISTS errors_log_severity ON errors_log (severity, created_at);
CREATE INDEX IF NOT EXISTS errors_log_created  ON errors_log (created_at);
CREATE INDEX IF NOT EXISTS errors_log_type     ON errors_log (error_type, created_at);
CREATE TABLE IF NOT EXISTS cards (
  card_id             TEXT PRIMARY KEY,
  session_id          TEXT NOT NULL,
  gist                TEXT,
  valence             TEXT,
  salience            TEXT,
  groundedness        TEXT,
  topics              JSONB,
  agent_id            TEXT,
  agent_name          TEXT,
  username            TEXT,
  created_at          TIMESTAMPTZ,
  source              JSONB,
  confidence          REAL NOT NULL DEFAULT 1.0,
  superseded_by       JSONB,
  supersedes          JSONB,
  schema_version      INTEGER NOT NULL DEFAULT 1,
  computed_at         TIMESTAMPTZ,
  consolidation_model TEXT
);
CREATE INDEX IF NOT EXISTS cards_session          ON cards (session_id);
CREATE INDEX IF NOT EXISTS cards_agent            ON cards (agent_id, created_at);
CREATE INDEX IF NOT EXISTS cards_recency_salience ON cards (created_at DESC, salience);
"""

# Separat, weil CREATE OR REPLACE VIEW Ownership der View erfordert.
# Wird in mirror.init() in eigenem try-except ausgeführt, damit Tabellen-DDL
# auch dann committed wird wenn der User die View nicht ersetzen darf.
DDL_VIEW = """
-- session_metrics: aggregierter Read-View. tool_calls existiert im Mirror nicht
-- (siehe events-Tabelle für Tool-Telemetrie) — daher fehlt tool_calls/successes/
-- errors/truncates im PG-View. Reine SQLite-Quelle ist authoritative für Tools.
CREATE OR REPLACE VIEW session_metrics AS
SELECT
    s.id                                       AS session_id,
    s.agent_id, s.username AS user_id, s.project_id,
    s.started_at AS created_at, s.updated_at, s.status,
    COALESCE(llm.calls, 0)                     AS llm_calls,
    COALESCE(llm.input_tokens, 0)              AS input_tokens,
    COALESCE(llm.output_tokens, 0)             AS output_tokens,
    COALESCE(llm.cache_read_tokens, 0)         AS cache_read_tokens,
    COALESCE(llm.cache_creation_tokens, 0)     AS cache_creation_tokens,
    COALESCE(llm.cost_micros, 0)               AS cost_micros,
    COALESCE(llm.total_llm_ms, 0)              AS total_llm_ms,
    COALESCE(cmp.events, 0)                    AS compactions,
    COALESCE(cmp.skipped, 0)                   AS compactions_skipped,
    COALESCE(err.events, 0)                    AS errors
FROM sessions s
LEFT JOIN (
    SELECT session_id,
           COUNT(*)                            AS calls,
           SUM(prompt_tokens)                  AS input_tokens,
           SUM(completion_tokens)              AS output_tokens,
           SUM(cache_read_tokens)              AS cache_read_tokens,
           SUM(cache_creation_tokens)          AS cache_creation_tokens,
           SUM(cost_micros)                    AS cost_micros,
           SUM(total_ms)                       AS total_llm_ms
    FROM llm_calls GROUP BY session_id
) llm ON llm.session_id = s.id
LEFT JOIN (
    SELECT session_id,
           COUNT(*)                                                AS events,
           SUM(CASE WHEN skipped THEN 1 ELSE 0 END)                AS skipped
    FROM compaction_events GROUP BY session_id
) cmp ON cmp.session_id = s.id
LEFT JOIN (
    SELECT session_id, COUNT(*) AS events
    FROM errors_log WHERE session_id IS NOT NULL GROUP BY session_id
) err ON err.session_id = s.id;
"""

DDL_BASE = DDL_TABLES + DDL_VIEW


async def ensure_embed_col(conn, table: str = "events") -> None:
    """Legt die embedding-Spalte einer Tabelle mit der richtigen Dimension an
    oder passt sie an. Generisch über `table` (events, cards) — dieselbe
    Dim-Quelle (`embed_model`), damit beide im selben pgvector-Raum vergleichbar
    sind. `table` ist intern/vertrauenswürdig (kein User-Input)."""
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import dim_for_model
    model = load_config().get("embed_model", "")
    dim = dim_for_model(model) if model else 0
    if not dim:
        return

    row = await conn.fetchrow(f"""
        SELECT format_type(atttypid, atttypmod) AS coltype
        FROM pg_attribute
        WHERE attrelid = '{table}'::regclass AND attname = 'embedding' AND attnum > 0
    """)
    if row:
        if row["coltype"] == f"vector({dim})":
            return
        logger.info("Embedding-Dimension geändert (%s → vector(%d)) auf %s — Spalte neu anlegen", row["coltype"], dim, table)
        await conn.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedding")
        await conn.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedding_model")
        await conn.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedded_at")

    await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding vector({dim})")
    await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding_model TEXT")
    await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ")
    try:
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {table}_embedding_hnsw
            ON {table} USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        logger.info("Embedding-Spalte vector(%d) + HNSW-Index auf %s bereit", dim, table)
    except Exception:
        try:
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {table}_embedding_ivfflat
                ON {table} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            logger.info("Embedding-Spalte vector(%d) + IVFFlat-Index auf %s bereit (HNSW nicht unterstützt)", dim, table)
        except Exception as e:
            logger.warning("Kein Vektor-Index auf %s angelegt (pgvector zu alt?): %s — Suche läuft per Seq-Scan", table, e)
