"""PostgreSQL Datamining-Mirror.

Spiegelt alle Messages blockweise in PG — fire-and-forget, kein Retry.
Aktiviert wenn settings.pg_mirror_dsn gesetzt ist, sonst kompletter No-op.

State (`_pool`, `_backfill_running`) lebt in diesem Modul. Sub-Module:
- `_mirror_explode.py`: Message → Events (pure)
- `_mirror_ddl.py`: Schema-DDL + Embedding-Spalten-Sync
- `_mirror_embed.py`: Embedding-Calls + Backfill (Pool als Parameter)
- `_mirror_writes.py`: INSERT-Pfade (Pool als Parameter)
"""
from __future__ import annotations

import asyncio
import logging

from hydrahive.db._message_model import Message
from hydrahive.db._mirror_ddl import DDL_TABLES, DDL_VIEW, ensure_embed_col
from hydrahive.db._mirror_embed import (
    backfill_loop,
    embed_event as _embed_event_impl,
    embed_text as _embed_text_impl,
    queue_embed as _queue_embed_impl,
)
from hydrahive.db._mirror_explode import (
    CHUNK_CHARS,
    explode as _explode_impl,
    parse_ts as _parse_ts,
)
from hydrahive.db._mirror_writes import write_message, write_session
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
_backfill_task: "asyncio.Task | None" = None


# ---------------------------------------------------------------- lifecycle

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
            # Tabellen + Indexes zuerst — in eigenem Statement, damit sie auch
            # dann angelegt werden, wenn die View-Erstellung scheitert.
            await conn.execute(DDL_TABLES)
            try:
                await conn.execute(DDL_VIEW)
            except Exception as ve:
                # CREATE OR REPLACE VIEW scheitert wenn die View bereits existiert
                # und einem anderen DB-User gehört. Mirror läuft trotzdem weiter.
                logger.warning("PG-Mirror: session_metrics-View konnte nicht erstellt/ersetzt werden (Rechte?): %s", ve)
            try:
                await ensure_embed_col(conn)
            except Exception as ee:
                logger.warning("PG-Mirror: Embedding-Spalte konnte nicht angepasst werden (Rechte?): %s", ee)
            try:
                await ensure_embed_col(conn, table="cards")
            except Exception as ce:
                logger.warning("PG-Mirror: cards-Embedding-Spalte konnte nicht angepasst werden (Rechte?): %s", ce)
        logger.info("PG-Mirror bereit")
    except Exception as e:
        logger.warning("PG-Mirror init fehlgeschlagen — Mirror deaktiviert: %s", e)
        _pool = None


async def close() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def _cancel_backfill() -> None:
    """Bricht laufenden Backfill ab und wartet bis er wirklich beendet ist."""
    global _backfill_task
    if _backfill_task and not _backfill_task.done():
        _backfill_task.cancel()
        try:
            await _backfill_task
        except (asyncio.CancelledError, Exception):
            pass
    _backfill_task = None


async def on_embed_model_change(new_model: str) -> None:
    """Spalte anpassen + Backfill starten. Wird vom LLM-Save-Endpoint aufgerufen."""
    global _backfill_task
    if not _pool:
        return
    await _cancel_backfill()
    async with _pool.acquire() as conn:
        await ensure_embed_col(conn)
    if new_model:
        try:
            _backfill_task = asyncio.get_running_loop().create_task(_run_backfill(new_model))
        except RuntimeError:
            pass


async def reset_embeddings(event_type: str | None = None) -> int:
    """Setzt Embeddings zurück damit der Backfill sie neu einbettet."""
    if not _pool:
        return 0
    await _cancel_backfill()
    async with _pool.acquire() as conn:
        if event_type:
            r = await conn.execute(
                "UPDATE events SET embedding=NULL, embedding_model=NULL, embedded_at=NULL WHERE event_type=$1",
                event_type, timeout=300,
            )
        else:
            r = await conn.execute(
                "UPDATE events SET embedding=NULL, embedding_model=NULL, embedded_at=NULL",
                timeout=300,
            )
    count = int(r.split()[-1])
    return count


async def _run_backfill(model: str, batch_size: int = 100) -> None:
    global _backfill_running
    _backfill_running = True
    try:
        await backfill_loop(_pool, model, batch_size)
    except asyncio.CancelledError:
        logger.info("Backfill abgebrochen (model=%s)", model)
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
        asyncio.get_running_loop().create_task(write_message(_pool, m, s))
    except RuntimeError:
        pass


def schedule_session(s: Session) -> None:
    """Von sessions.create() / sessions.update() aufgerufen — sync, fire-and-forget."""
    if not _pool:
        return
    try:
        asyncio.get_running_loop().create_task(write_session(_pool, s))
    except RuntimeError:
        pass


# ---------------------------------------------------------------- legacy aliases

# Externe Importer (mirror_import_sqlite, Tests) nutzen die alten Namen.
def _explode(m: Message, s: Session) -> list[dict]:
    return _explode_impl(m, s)


async def _embed_event(event_id: str, text: str, model: str) -> None:
    await _embed_event_impl(_pool, event_id, text, model)


def _queue_embed(events: list[dict]) -> None:
    _queue_embed_impl(_pool, events)


def _embed_text(e: dict) -> str | None:
    return _embed_text_impl(e)
