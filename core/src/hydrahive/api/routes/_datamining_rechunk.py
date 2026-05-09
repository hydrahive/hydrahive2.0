"""Rechunk-Implementation: schneidet zu lange tool_result-Events neu in CHUNK_CHARS-Blöcke."""
from __future__ import annotations

import logging

from hydrahive.db import mirror

logger = logging.getLogger(__name__)


async def run_rechunk() -> None:
    chunk_chars = mirror.CHUNK_CHARS
    rechunked = deleted = inserted = 0
    try:
        async with mirror._pool.acquire() as conn:
            # Alle (message_id, block_index) Paare wo irgendein Chunk zu lang ist
            groups = await conn.fetch("""
                SELECT DISTINCT message_id, block_index
                FROM events
                WHERE event_type = 'tool_result'
                  AND length(tool_output) > $1
            """, chunk_chars)

        for g in groups:
            mid, bi = g["message_id"], g["block_index"]
            async with mirror._pool.acquire() as conn:
                chunks = await conn.fetch("""
                    SELECT chunk_index, tool_output, tool_use_id, is_error,
                           username, agent_id, agent_name, project_id,
                           session_id, token_count, created_at
                    FROM events
                    WHERE message_id = $1 AND block_index = $2 AND event_type = 'tool_result'
                    ORDER BY chunk_index
                """, mid, bi)
            if not chunks:
                continue

            full_text = "".join(c["tool_output"] or "" for c in chunks)
            new_chunks = [full_text[i:i + chunk_chars] for i in range(0, len(full_text), chunk_chars)]
            base = dict(chunks[0])

            async with mirror._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM events WHERE message_id=$1 AND block_index=$2 AND event_type='tool_result'",
                    mid, bi,
                )
                deleted += len(chunks)
                await conn.executemany("""
                    INSERT INTO events (id, message_id, session_id, block_index,
                      chunk_index, chunk_total, username, agent_id, agent_name,
                      project_id, event_type, tool_use_id, tool_output, is_error,
                      token_count, created_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'tool_result',$11,$12,$13,$14,$15)
                    ON CONFLICT (id) DO NOTHING
                """, [
                    (f"{mid}:{bi}:{ci}", mid, base["session_id"], bi,
                     ci, len(new_chunks),
                     base["username"], base["agent_id"], base["agent_name"], base["project_id"],
                     base["tool_use_id"], chunk, base["is_error"],
                     base["token_count"], base["created_at"])
                    for ci, chunk in enumerate(new_chunks)
                ])
                inserted += len(new_chunks)
            rechunked += 1

        logger.info("Rechunk abgeschlossen: %d Gruppen, %d alte → %d neue Chunks", rechunked, deleted, inserted)
    except Exception as e:
        logger.warning("Rechunk fehlgeschlagen: %s", e)
