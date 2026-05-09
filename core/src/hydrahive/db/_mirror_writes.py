"""Mirror — INSERTs für Sessions und Messages. Pool als Parameter."""
from __future__ import annotations

import json
import logging

from hydrahive.db._message_model import Message
from hydrahive.db._mirror_embed import queue_embed
from hydrahive.db._mirror_explode import agent_name, explode, parse_ts
from hydrahive.db.sessions import Session

logger = logging.getLogger(__name__)


async def write_session(pool, s: Session) -> None:
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (id, username, agent_id, agent_name, project_id,
                                      title, status, started_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (id) DO UPDATE SET
                  title=EXCLUDED.title, status=EXCLUDED.status,
                  updated_at=EXCLUDED.updated_at
            """, s.id, s.user_id, s.agent_id, agent_name(s.agent_id),
                s.project_id, s.title, s.status,
                parse_ts(s.created_at), parse_ts(s.updated_at))
    except Exception as e:
        logger.warning("PG-Mirror session %s fehlgeschlagen: %s", s.id, e)


async def write_message(pool, m: Message, s: Session) -> None:
    if pool is None:
        return
    events = explode(m, s)
    if not events:
        return
    try:
        async with pool.acquire() as conn:
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
                    parse_ts(e["created_at"]),
                )
                for e in events
            ])
        queue_embed(pool, events)
    except Exception as e:
        logger.warning("PG-Mirror message %s fehlgeschlagen: %s", m.id, e)
