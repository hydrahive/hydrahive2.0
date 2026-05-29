"""Claude-Code-Transkript-JSONL → mirror-fähige Message-Dicts (reine Funktion)."""
from __future__ import annotations

import json


def parse_entries(lines: list[str]) -> list[dict]:
    """Filtert auf user/assistant-Einträge mit message.role+content.

    Andere Entry-Typen (system, attachment, file-history-snapshot, ai-title,
    last-prompt, permission-mode) werden übersprungen. Jeder Treffer:
    {message_id, role, content, created_at}. message_id = stabile Transkript-UUID.
    """
    out: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") not in ("user", "assistant"):
            continue
        msg = e.get("message")
        uuid = e.get("uuid")
        if not isinstance(msg, dict) or not uuid:
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant") or content is None:
            continue
        out.append({
            "message_id": uuid,
            "role": role,
            "content": content,
            "created_at": e.get("timestamp"),
        })
    return out
