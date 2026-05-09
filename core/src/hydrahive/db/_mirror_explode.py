"""Mirror — pure functions: Message → Events, chunking, timestamps."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from hydrahive.db._message_model import Message
from hydrahive.db.sessions import Session
from hydrahive.settings import settings

CHUNK_CHARS = 3000


def explode(m: Message, s: Session) -> list[dict]:
    """Splittet eine Message in Event-Dicts für die PG-Mirror-Tabelle.

    text/thinking/tool_use sind je ein Event; tool_result wird in Chunks
    von CHUNK_CHARS aufgeteilt damit die PG-Zeilen handhabbar bleiben.
    """
    base: dict[str, Any] = {
        "message_id": m.id, "session_id": m.session_id,
        "username": s.user_id, "agent_id": s.agent_id,
        "agent_name": agent_name(s.agent_id), "project_id": s.project_id,
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


def agent_name(agent_id: str) -> str:
    try:
        p = settings.agents_dir / agent_id / "config.json"
        return json.loads(p.read_text()).get("name", agent_id)
    except Exception:
        return agent_id


def parse_ts(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
