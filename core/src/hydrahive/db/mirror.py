"""PostgreSQL Datamining-Mirror.

Spiegelt alle Messages blockweise in PG — fire-and-forget, kein Retry.
Aktiviert wenn settings.pg_mirror_dsn gesetzt ist, sonst kompletter No-op.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from hydrahive.db._message_model import Message
from hydrahive.db.sessions import Session
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    _HAS_ASYNCPG = False

_pool: "asyncpg.Pool | None" = None
_backfill_running: bool = False
CHUNK_CHARS = 8000

_DDL_BASE = """
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
"""


async def init() -> None:
    global _pool
    if not _HAS_ASYNCPG:
        logger.warning("Mirror: asyncpg nicht installiert — Mirror deaktiviert")
        return
    dsn = settings.pg_mirror_dsn
    if not dsn:
        return
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4, command_timeout=10)
        async with _pool.acquire() as conn:
            await conn.execute(_DDL_BASE)
            await _ensure_embed_col(conn)
        logger.info("PG-Mirror bereit")
    except Exception as e:
        logger.warning("PG-Mirror init fehlgeschlagen — Mirror deaktiviert: %s", e)
        _pool = None


async def _ensure_embed_col(conn: "asyncpg.Connection") -> None:
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
    await conn.execute(f"""
        CREATE INDEX IF NOT EXISTS events_embedding_hnsw
        ON events USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    logger.info("Embedding-Spalte vector(%d) + HNSW-Index bereit", dim)


async def close() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def on_embed_model_change(new_model: str) -> None:
    """Spalte anpassen + Backfill starten. Wird vom LLM-Save-Endpoint aufgerufen."""
    if not _pool:
        return
    async with _pool.acquire() as conn:
        await _ensure_embed_col(conn)
    if new_model:
        try:
            asyncio.get_running_loop().create_task(_backfill_task(new_model))
        except RuntimeError:
            pass


async def reset_embeddings(event_type: str | None = None) -> int:
    """Setzt Embeddings zurück damit der Backfill sie neu einbettet."""
    if not _pool:
        return 0
    async with _pool.acquire() as conn:
        if event_type:
            r = await conn.execute(
                "UPDATE events SET embedding=NULL, embedding_model=NULL, embedded_at=NULL WHERE event_type=$1",
                event_type,
            )
        else:
            r = await conn.execute(
                "UPDATE events SET embedding=NULL, embedding_model=NULL, embedded_at=NULL"
            )
    count = int(r.split()[-1])
    return count


async def _backfill_task(model: str, batch_size: int = 200) -> None:
    global _backfill_running
    if _backfill_running:
        logger.info("Backfill läuft bereits — übersprungen")
        return
    _backfill_running = True
    total = 0
    try:
        from hydrahive.llm.embed import aembed_batch
        while True:
            if not _pool:
                break
            async with _pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, tool_name,
                           coalesce(text, tool_output, tool_input::text) AS content
                    FROM events
                    WHERE embedding IS NULL
                      AND (text IS NOT NULL OR tool_output IS NOT NULL OR tool_input IS NOT NULL)
                    ORDER BY created_at
                    LIMIT $1
                """, batch_size)
            if not rows:
                break
            texts = [
                f"{r['tool_name']}: {r['content']}" if r["tool_name"] else r["content"]
                for r in rows
            ]
            vectors = await aembed_batch(texts, model)
            vec_str = lambda v: "[" + ",".join(str(x) for x in v) + "]" if v else None
            updates = [
                (vec_str(vectors[i]), model, rows[i]["id"])
                for i in range(len(rows))
                if vectors[i] is not None
            ]
            if updates:
                async with _pool.acquire() as conn:
                    await conn.executemany("""
                        UPDATE events SET embedding=$1::vector, embedding_model=$2, embedded_at=now()
                        WHERE id=$3 AND embedding IS NULL
                    """, updates)
            total += len(rows)
            if len(rows) < batch_size:
                break
            await asyncio.sleep(0.05)
        logger.info("Backfill abgeschlossen: %d Events eingebettet", total)
    except Exception as e:
        logger.warning("Backfill fehlgeschlagen nach %d Events: %s", total, e)
    finally:
        _backfill_running = False


# ---------------------------------------------------------------- public query

async def recent_events(limit: int = 100) -> list[dict]:
    """Letzte N Events für die Datamining-Seite."""
    if not _pool:
        return []
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, session_id, username, agent_name, event_type,
                       created_at, tool_name, is_error,
                       left(coalesce(text, tool_output, tool_input::text, ''), 200) AS snippet
                FROM events
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("PG-Mirror recent_events fehlgeschlagen: %s", e)
        return []


# ---------------------------------------------------------------- public hooks

def schedule_message(m: Message, s: Session) -> None:
    """Von messages.append() aufgerufen — sync, fire-and-forget."""
    if not _pool:
        return
    try:
        asyncio.get_running_loop().create_task(_write_message(m, s))
    except RuntimeError:
        pass


def schedule_session(s: Session) -> None:
    """Von sessions.create() / sessions.update() aufgerufen — sync, fire-and-forget."""
    if not _pool:
        return
    try:
        asyncio.get_running_loop().create_task(_write_session(s))
    except RuntimeError:
        pass


# ---------------------------------------------------------------- internals

async def _write_session(s: Session) -> None:
    try:
        async with _pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (id, username, agent_id, agent_name, project_id,
                                      title, status, started_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (id) DO UPDATE SET
                  title=EXCLUDED.title, status=EXCLUDED.status,
                  updated_at=EXCLUDED.updated_at
            """, s.id, s.user_id, s.agent_id, _agent_name(s.agent_id),
                s.project_id, s.title, s.status,
                _parse_ts(s.created_at), _parse_ts(s.updated_at))
    except Exception as e:
        logger.warning("PG-Mirror session %s fehlgeschlagen: %s", s.id, e)


async def _write_message(m: Message, s: Session) -> None:
    events = _explode(m, s)
    if not events:
        return
    try:
        async with _pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO events (id, message_id, session_id, block_index,
                  chunk_index, chunk_total, username, agent_id, agent_name,
                  project_id, event_type, text, tool_name, tool_use_id,
                  tool_input, tool_output, is_error, token_count, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
                ON CONFLICT (id) DO NOTHING
            """, [
                (
                    e["id"], e["message_id"], e["session_id"], e["block_index"],
                    e["chunk_index"], e["chunk_total"], e["username"], e["agent_id"],
                    e["agent_name"], e["project_id"], e["event_type"], e.get("text"),
                    e.get("tool_name"), e.get("tool_use_id"),
                    json.dumps(e["tool_input"]) if e.get("tool_input") is not None else None,
                    e.get("tool_output"), e.get("is_error"), e.get("token_count"),
                    _parse_ts(e["created_at"]),
                )
                for e in events
            ])
        _queue_embed(events)
    except Exception as e:
        logger.warning("PG-Mirror message %s fehlgeschlagen: %s", m.id, e)


def _queue_embed(events: list[dict]) -> None:
    from hydrahive.llm._config import load_config
    import json as _json
    model = load_config().get("embed_model", "")
    if not model:
        return
    for e in events:
        text = _embed_text(e)
        if text:
            try:
                asyncio.get_running_loop().create_task(_embed_event(e["id"], text, model))
            except RuntimeError:
                pass


def _embed_text(e: dict) -> str | None:
    """Baut den Text der eingebettet wird — tool_name immer voranstellen."""
    import json as _json
    ti = e.get("tool_input")
    tool_name = e.get("tool_name", "")
    base = e.get("text") or e.get("tool_output") or (_json.dumps(ti, ensure_ascii=False) if ti else None)
    if not base:
        return None
    if tool_name:
        return f"{tool_name}: {base}"
    return base


async def _embed_event(event_id: str, text: str, model: str) -> None:
    from hydrahive.llm.embed import aembed
    vec = await aembed(text, model)
    if vec is None or not _pool:
        return
    vec_str = "[" + ",".join(str(x) for x in vec) + "]"
    try:
        async with _pool.acquire() as conn:
            await conn.execute("""
                UPDATE events SET embedding=$1::vector, embedding_model=$2, embedded_at=now()
                WHERE id=$3 AND embedding IS NULL
            """, vec_str, model, event_id)
    except Exception as e:
        logger.warning("Embedding-Speichern fehlgeschlagen (%s): %s", event_id, e)


def _explode(m: Message, s: Session) -> list[dict]:
    base: dict[str, Any] = {
        "message_id": m.id, "session_id": m.session_id,
        "username": s.user_id, "agent_id": s.agent_id,
        "agent_name": _agent_name(s.agent_id), "project_id": s.project_id,
        "token_count": m.token_count, "created_at": m.created_at,
    }

    content = m.content

    if m.role == "compaction":
        text = content if isinstance(content, str) else str(content)
        return [{**base, "id": f"{m.id}:0:0", "block_index": 0,
                 "chunk_index": 0, "chunk_total": 1, "event_type": "compaction", "text": text}]

    blocks: list = ([{"type": "text", "text": content}] if isinstance(content, str)
                    else content if isinstance(content, list) else [])

    events: list[dict] = []
    for bi, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")

        if btype == "text":
            etype = "user_input" if m.role == "user" else "assistant_text"
            events.append({**base, "id": f"{m.id}:{bi}:0", "block_index": bi,
                           "chunk_index": 0, "chunk_total": 1,
                           "event_type": etype, "text": block.get("text", "")})

        elif btype == "thinking":
            events.append({**base, "id": f"{m.id}:{bi}:0", "block_index": bi,
                           "chunk_index": 0, "chunk_total": 1,
                           "event_type": "thinking",
                           "text": block.get("thinking") or block.get("text", "")})

        elif btype == "tool_use":
            events.append({**base, "id": f"{m.id}:{bi}:0", "block_index": bi,
                           "chunk_index": 0, "chunk_total": 1,
                           "event_type": "tool_call",
                           "tool_name": block.get("name"),
                           "tool_use_id": block.get("id"),
                           "tool_input": block.get("input")})

        elif btype == "tool_result":
            raw = block.get("content", "")
            if isinstance(raw, list):
                raw = "\n".join(p.get("text", "") for p in raw
                                if isinstance(p, dict) and p.get("type") == "text")
            elif not isinstance(raw, str):
                raw = str(raw)
            chunks = _chunks(raw, CHUNK_CHARS)
            for ci, chunk in enumerate(chunks):
                events.append({**base, "id": f"{m.id}:{bi}:{ci}", "block_index": bi,
                                "chunk_index": ci, "chunk_total": len(chunks),
                                "event_type": "tool_result",
                                "tool_use_id": block.get("tool_use_id"),
                                "tool_output": chunk,
                                "is_error": block.get("is_error", False)})

    return events


def _chunks(text: str, size: int) -> list[str]:
    if not text or len(text) <= size:
        return [text] if text else [""]
    return [text[i:i + size] for i in range(0, len(text), size)]


def _agent_name(agent_id: str) -> str:
    try:
        p = settings.agents_dir / agent_id / "config.json"
        return json.loads(p.read_text()).get("name", agent_id)
    except Exception:
        return agent_id


def _parse_ts(ts: str | None):
    if not ts:
        return None
    from datetime import datetime, timezone
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
