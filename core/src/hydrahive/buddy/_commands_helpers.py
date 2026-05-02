"""Internal helpers for buddy commands (no LLM calls)."""
from __future__ import annotations

import re

from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db

_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def slug(s: str) -> str:
    return _SLUG_RE.sub("-", s.strip().lower()).strip("-") or "note"


def extract_text_from_content(content) -> str:
    """Concatenate text parts from a DB message content (str or list[ContentBlock])."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                t = b.get("text", "")
                if t:
                    parts.append(t)
        return " ".join(parts).strip()
    return ""


def snapshot_active_session(buddy: dict, username: str, last_n: int = 30) -> str:
    """Markdown dump of last N user/assistant messages from the buddy's active session."""
    sessions = [s for s in sessions_db.list_for_user(username)
                if s.agent_id == buddy["id"]]
    if not sessions:
        return ""
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    msgs = messages_db.list_for_session(sessions[0].id)
    msgs = [m for m in msgs if m.role in ("user", "assistant")][-last_n:]
    lines: list[str] = []
    for m in msgs:
        text = extract_text_from_content(m.content)
        if not text:
            continue
        who = "User" if m.role == "user" else buddy.get("name", "Buddy")
        lines.append(f"**{who}:** {text}")
    return "\n\n".join(lines)
