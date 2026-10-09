"""Nachtrag: gekürzte Werkzeug-Ausgaben vollständig in den Index (docs/specs/datamining-volltext-werkzeuge.md).

Liest ``tool_calls`` (SQLite, nur lesend), sucht das Original-Ergebnis-Ereignis im Index (gleiche ``tool_use_id``,
gleiche Sitzung) und schreibt den abgeschnittenen Rest als neue Stücke. Schreibt nur NEUE Zeilen
(``ON CONFLICT DO NOTHING``) – nichts Bestehendes wird geändert, ein zweiter Lauf schreibt 0.
"""
from __future__ import annotations

import logging

from hydrahive.db._mirror_fulltext import SKIP_EMBED, build_events

logger = logging.getLogger(__name__)

PAGE = 50

_BASE_SQL = """
    SELECT DISTINCT ON (tool_use_id) tool_use_id, message_id, session_id, block_index, username, agent_id,
           agent_name, project_id, created_at
    FROM events
    WHERE event_type = 'tool_result' AND tool_use_id = ANY($1::text[])
    ORDER BY tool_use_id, chunk_index
"""

_INSERT_SQL = """
    INSERT INTO events (id, message_id, session_id, block_index, chunk_index, chunk_total, username, agent_id,
      agent_name, project_id, event_type, tool_name, tool_use_id, tool_output, is_error, created_at,
      embedding_model)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
    ON CONFLICT (id) DO NOTHING
"""


def _calls(after: str, limit: int) -> list[dict]:
    from hydrahive.db.connection import db
    with db() as conn:
        rows = conn.execute(
            """SELECT id, tool_name, tool_use_id, session_id, result, truncate_limit_chars, status
               FROM tool_calls
               WHERE result_truncated = 1 AND tool_use_id IS NOT NULL AND id > ?
               ORDER BY id LIMIT ?""", (after, limit)).fetchall()
    return [dict(r) for r in rows]


async def backfill_fulltext(pool) -> dict:
    """Trägt alle gekürzten Ausgaben nach. Rückgabe: Zähler (geprüft, ohne Original im Index, Stücke neu)."""
    stats = {"calls": 0, "no_base": 0, "written": 0}
    if pool is None:
        return stats
    after = ""
    while True:
        calls = _calls(after, PAGE)
        if not calls:
            break
        after = calls[-1]["id"]
        stats["calls"] += len(calls)
        async with pool.acquire() as conn:
            bases = {r["tool_use_id"]: dict(r) for r in await conn.fetch(
                _BASE_SQL, [c["tool_use_id"] for c in calls])}
            rows = []
            for c in calls:
                base = bases.get(c["tool_use_id"])
                if base is None or base["session_id"] != c["session_id"]:
                    stats["no_base"] += 1
                    continue
                for e in build_events(c, base):
                    rows.append((e["id"], e["message_id"], e["session_id"], e["block_index"], e["chunk_index"],
                                 e["chunk_total"], e["username"], e["agent_id"], e["agent_name"], e["project_id"],
                                 e["event_type"], e["tool_name"], e["tool_use_id"], e["tool_output"], e["is_error"],
                                 e["created_at"], SKIP_EMBED))
            if rows:
                before = await conn.fetchval("SELECT count(*) FROM events WHERE id = ANY($1::text[])", [r[0] for r in rows])
                await conn.executemany(_INSERT_SQL, rows)
                stats["written"] += len(rows) - before          # bereits vorhandene zählen nicht (idempotent)
        if len(calls) < PAGE:
            break
    logger.info("Volltext-Nachtrag: %s", stats)
    return stats
