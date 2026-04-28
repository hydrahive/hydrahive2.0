from __future__ import annotations

import json
from typing import Any

from hydrahive.compaction.redact import redact
from hydrahive.db.messages import Message

_TOOL_RESULT_LIMIT = 2000


def serialize_for_summary(messages: list[Message]) -> str:
    """Convert messages to flat text format for the summarizer LLM.

    Plain text — NOT chat format — so the model treats it as input to summarize
    instead of trying to continue the conversation. Tool results are truncated
    to 2000 chars to keep the request size bounded. Secrets get redacted.
    """
    lines: list[str] = []
    for m in messages:
        lines.extend(_render_message(m))
    return redact("\n".join(lines))


def _render_message(m: Message) -> list[str]:
    role = m.role
    content = m.content

    if role == "user":
        return _render_user(content)
    if role == "assistant":
        return _render_assistant(content)
    if role == "system":
        return [f"[System]: {_text_or_dump(content)}"]
    if role == "compaction":
        return [f"[Earlier summary]: {_text_or_dump(content)}"]
    return [f"[{role.title()}]: {_text_or_dump(content)}"]


def _render_user(content: Any) -> list[str]:
    if isinstance(content, str):
        return [f"[User]: {content}"]
    if isinstance(content, list):
        out: list[str] = []
        text_parts = []
        for block in content:
            if not isinstance(block, dict):
                text_parts.append(str(block))
                continue
            btype = block.get("type")
            if btype == "tool_result":
                txt = _truncate(_text_or_dump(block.get("content", "")), _TOOL_RESULT_LIMIT)
                tag = block.get("tool_use_id", "")[-8:]
                marker = " (error)" if block.get("is_error") else ""
                out.append(f"[Tool result {tag}{marker}]: {txt}")
            elif btype == "text":
                text_parts.append(block.get("text", ""))
            else:
                text_parts.append(_text_or_dump(block))
        if text_parts:
            out.insert(0, f"[User]: {' '.join(text_parts).strip()}")
        return out
    return [f"[User]: {_text_or_dump(content)}"]


def _render_assistant(content: Any) -> list[str]:
    if isinstance(content, str):
        return [f"[Assistant]: {content}"]
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                out.append(f"[Assistant]: {block}")
                continue
            btype = block.get("type")
            if btype == "text":
                out.append(f"[Assistant]: {block.get('text', '')}")
            elif btype == "thinking":
                out.append(f"[Assistant thinking]: {block.get('thinking', '')}")
            elif btype == "tool_use":
                args = json.dumps(block.get("input", {}), ensure_ascii=False)
                args = _truncate(args, 400)
                out.append(f"[Assistant tool call]: {block.get('name', '?')}({args})")
        return out
    return [f"[Assistant]: {_text_or_dump(content)}"]


def _text_or_dump(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n…[gekürzt: {len(s) - limit} Zeichen]"
