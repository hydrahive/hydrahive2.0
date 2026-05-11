"""Mirror — Schema-DDL und Embedding-Spalten-Management."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


DDL_BASE = """
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
"""


async def ensure_embed_col(conn) -> None:
    """Legt embedding-Spalte mit der richtigen Dimension an oder passt sie an."""
    from hydrahive.llm._config import load_config
    from hydrahive.llm.embed import dim_for_model
    model = load_config().get("embed_model", "")
    dim = dim_for_model(model) if model else 0
    if not dim:
        return

    row = await conn.fetchrow("""
        SELECT format_type(atttypid, atttypmod) AS coltype
        FROM pg_attribute
        WHERE attrelid = 'events'::regclass AND attname = 'embedding' AND attnum > 0
    """)
    if row:
        if row["coltype"] == f"vector({dim})":
            return
        logger.info("Embedding-Dimension geändert (%s → vector(%d)) — Spalte neu anlegen", row["coltype"], dim)
        await conn.execute("ALTER TABLE events DROP COLUMN IF EXISTS embedding")
        await conn.execute("ALTER TABLE events DROP COLUMN IF EXISTS embedding_model")
        await conn.execute("ALTER TABLE events DROP COLUMN IF EXISTS embedded_at")

    await conn.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS embedding vector({dim})")
    await conn.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS embedding_model TEXT")
    await conn.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ")
    try:
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS events_embedding_hnsw
            ON events USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        logger.info("Embedding-Spalte vector(%d) + HNSW-Index bereit", dim)
    except Exception:
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS events_embedding_ivfflat
                ON events USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            logger.info("Embedding-Spalte vector(%d) + IVFFlat-Index bereit (HNSW nicht unterstützt)", dim)
        except Exception as e:
            logger.warning("Kein Vektor-Index angelegt (pgvector zu alt?): %s — Suche läuft per Seq-Scan", e)
