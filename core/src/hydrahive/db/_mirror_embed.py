"""Mirror — Embedding-Calls + Backfill-Loop. Pool wird als Parameter durchgereicht."""
from __future__ import annotations

import asyncio
import json as _json
import logging

logger = logging.getLogger(__name__)

_EMBED_BATCH = 32  # Texte pro API-Call — reduziert Requests drastisch
# Kürzung nach Tokens statt nach Zeichen: db/_embed_clip.py (24.000 Zeichen waren bis 9.644 Tokens > 8.192).


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
                from hydrahive.db import _mirror_tasks
                if _mirror_tasks.closing:
                    return
                _mirror_tasks.track(embed_event(pool, e["id"], text, model))
            except RuntimeError:
                logger.debug("queue_embed: kein Event-Loop, Embedding-Task für Event %s übersprungen",
                             e.get("id", "?"))


def embed_text(e: dict) -> str | None:
    """Baut den Text der eingebettet wird — tool_name immer voranstellen."""
    ti = e.get("tool_input")
    tool_name = e.get("tool_name", "")
    base = e.get("text") or e.get("tool_output") or (_json.dumps(ti, ensure_ascii=False) if ti else None)
    if not base:
        return None
    from hydrahive.db._embed_clip import clip_for_embedding
    text = f"{tool_name}: {base}" if tool_name else base
    return clip_for_embedding(text)


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
                UPDATE events SET embedding=$1::text::vector, embedding_model=$2, embedded_at=now()
                WHERE id=$3 AND embedding IS NULL
            """, vec_str, model, event_id)
    except Exception as e:
        logger.warning("Embedding-Speichern fehlgeschlagen (%s): %s", event_id, e)


async def _store_batch(pool, ids: list[str], vecs: list, model: str) -> int:
    """Speichert eine Batch von Embeddings. Gibt Anzahl tatsächlich gespeicherter zurück."""
    stored = 0
    async with pool.acquire() as conn:
        for event_id, vec in zip(ids, vecs):
            if vec is None:
                continue
            vec_str = "[" + ",".join(str(x) for x in vec) + "]"
            try:
                await conn.execute("""
                    UPDATE events SET embedding=$1::text::vector, embedding_model=$2, embedded_at=now()
                    WHERE id=$3 AND embedding IS NULL
                """, vec_str, model, event_id)
                stored += 1
            except Exception as e:
                logger.warning("Embedding-Speichern fehlgeschlagen (%s): %s", event_id, e)
    return stored


async def _embed_sub(pool, sub: list[tuple[str, str]], model: str) -> int:
    """Ein Paket einbetten. Lehnt die API das ganze Paket ab (alle None), werden die Einträge einzeln
    versucht – ein kaputter Text darf die übrigen nicht mehr blockieren (Task 36caf245)."""
    from hydrahive.llm.embed import aembed_batch
    ids = [s[0] for s in sub]
    vecs = await aembed_batch([s[1] for s in sub], model)
    if len(sub) > 1 and all(v is None for v in vecs):
        vecs = [(await aembed_batch([text], model))[0] for _, text in sub]
        failed = [i for i, v in zip(ids, vecs) if v is None]
        if failed:
            logger.warning("Backfill: %d von %d Einträgen nicht einbettbar, übersprungen: %s",
                           len(failed), len(sub), failed[:5])
    return await _store_batch(pool, ids, vecs, model) if pool is not None else 0


async def backfill_loop(pool, model: str, batch_size: int = 200, sleep_between: float = 1.0) -> int:
    """Iteriert über noch nicht eingebettete Events und embedded sie batchweise.

    Läuft per Schlüssel-Blättern (created_at, id) VORWÄRTS durch: übersprungene Einträge bleiben hinten
    liegen statt jede Runde wieder vorn zu stehen (vorher hing der Nachtrag dauerhaft an denselben 200).
    Abbruch nur, wenn eine ganze Runde nichts speichern konnte (API nicht erreichbar).

    Returns: Gesamtzahl der eingebetteten Events.
    """
    from hydrahive.db._embed_clip import clip_for_embedding

    total = 0
    after: tuple = (None, "")
    logger.info("Backfill gestartet (model=%s, batch=%d, embed_batch=%d)", model, batch_size, _EMBED_BATCH)
    try:
        while True:
            if pool is None:
                break
            async with pool.acquire() as conn:
                rows = await conn.fetch(_BACKFILL_SQL, batch_size, after[0], after[1])
            if not rows:
                break
            after = (rows[-1]["created_at"], rows[-1]["id"])
            items = [(r["id"], clip_for_embedding(f"{r['tool_name']}: {r['content']}" if r["tool_name"]
                                                  else r["content"])) for r in rows]

            batch_stored = 0
            for i in range(0, len(items), _EMBED_BATCH):
                batch_stored += await _embed_sub(pool, items[i:i + _EMBED_BATCH], model)
                if i + _EMBED_BATCH < len(items):
                    await asyncio.sleep(sleep_between)

            total += batch_stored
            logger.info("Backfill: %d eingebettet (Batch: %d/%d erfolgreich)", total, batch_stored, len(rows))
            if batch_stored == 0:
                logger.error("Backfill abgebrochen: kein einziges Event gespeichert — API-Fehler oder alle Texte ungültig")
                break
            if len(rows) < batch_size:
                break
            await asyncio.sleep(sleep_between)

        logger.info("Backfill abgeschlossen: %d Events eingebettet", total)
    except Exception as e:
        logger.warning("Backfill fehlgeschlagen nach %d Events: %s", total, e)
    return total


_BACKFILL_SQL = """
    SELECT id, tool_name, created_at,
           coalesce(nullif(text,''), nullif(tool_output,''), nullif(tool_input::text,'')) AS content
    FROM events
    WHERE embedding IS NULL
      AND coalesce(embedding_model, '') NOT LIKE 'skip:%'
      AND (nullif(text,'') IS NOT NULL OR nullif(tool_output,'') IS NOT NULL OR nullif(tool_input::text,'') IS NOT NULL)
      AND ($2::timestamptz IS NULL OR (created_at, id) > ($2::timestamptz, $3::text))
    ORDER BY created_at, id
    LIMIT $1
"""
