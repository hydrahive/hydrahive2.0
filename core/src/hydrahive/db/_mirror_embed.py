"""Mirror — Embedding-Calls + Backfill-Loop. Pool wird als Parameter durchgereicht."""
from __future__ import annotations

import asyncio
import json as _json
import logging

logger = logging.getLogger(__name__)


def queue_embed(pool, events: list[dict]) -> None:
    """Plant Embedding-Berechnung für alle Events mit Inhalt im aktuellen Loop."""
    from hydrahive.llm._config import load_config
    model = load_config().get("embed_model", "")
    if not model:
        return
    for e in events:
        text = embed_text(e)
        if text:
            try:
                asyncio.get_running_loop().create_task(embed_event(pool, e["id"], text, model))
            except RuntimeError:
                pass


def embed_text(e: dict) -> str | None:
    """Baut den Text der eingebettet wird — tool_name immer voranstellen."""
    ti = e.get("tool_input")
    tool_name = e.get("tool_name", "")
    base = e.get("text") or e.get("tool_output") or (_json.dumps(ti, ensure_ascii=False) if ti else None)
    if not base:
        return None
    if tool_name:
        return f"{tool_name}: {base}"
    return base


async def embed_event(pool, event_id: str, text: str, model: str) -> None:
    if not text or not text.strip():
        return
    from hydrahive.llm.embed import aembed
    vec = await aembed(text, model)
    if vec is None or pool is None:
        logger.warning("Embedding None für Event %s (model=%s, text_len=%d)", event_id, model, len(text))
        return
    vec_str = "[" + ",".join(str(x) for x in vec) + "]"
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE events SET embedding=$1::vector, embedding_model=$2, embedded_at=now()
                WHERE id=$3 AND embedding IS NULL
            """, vec_str, model, event_id)
    except Exception as e:
        logger.warning("Embedding-Speichern fehlgeschlagen (%s): %s", event_id, e)


async def backfill_loop(pool, model: str, batch_size: int = 100) -> int:
    """Iteriert über noch nicht eingebettete Events und embedded sie batchweise.

    Returns: Gesamtzahl der eingebetteten Events.
    Caller verwaltet das `_backfill_running`-Flag.
    """
    total = 0
    logger.info("Backfill gestartet (model=%s)", model)
    try:
        while True:
            if pool is None:
                break
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, tool_name,
                           coalesce(nullif(text,''), nullif(tool_output,''), nullif(tool_input::text,'')) AS content
                    FROM events
                    WHERE embedding IS NULL
                      AND (nullif(text,'') IS NOT NULL OR nullif(tool_output,'') IS NOT NULL OR nullif(tool_input::text,'') IS NOT NULL)
                    ORDER BY created_at
                    LIMIT $1
                """, batch_size)
            if not rows:
                break
            sem = asyncio.Semaphore(5)

            async def _limited(r) -> None:
                async with sem:
                    text = f"{r['tool_name']}: {r['content']}" if r["tool_name"] else r["content"]
                    await embed_event(pool, r["id"], text, model)

            await asyncio.gather(*[_limited(r) for r in rows], return_exceptions=True)
            total += len(rows)
            logger.info("Backfill: %d eingebettet", total)
            if len(rows) < batch_size:
                break
            await asyncio.sleep(1.0)
        logger.info("Backfill abgeschlossen: %d Events eingebettet", total)
    except Exception as e:
        logger.warning("Backfill fehlgeschlagen nach %d Events: %s", total, e)
    return total
