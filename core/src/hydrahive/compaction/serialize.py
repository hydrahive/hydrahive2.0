from __future__ import annotations

import json
from typing import Any

from hydrahive.compaction.redact import redact
from hydrahive.db.messages import Message

DEFAULT_TOOL_RESULT_LIMIT = 2000
# Höchstlänge je Text-Block (Nutzer, Assistent, Denken, System, frühere Zusammenfassung). Großzügig – normale
# Nachrichten bleiben unverändert; nur echte Riesen (eingefügte Akten, Logs) werden gekürzt (Task 5406d099).
TEXT_BLOCK_LIMIT = 60_000
# Unbekannte Blöcke beim Nutzer: als JSON, aber gekürzt.
UNKNOWN_BLOCK_LIMIT = 2_000


def serialize_for_summary(
    messages: list[Message],
    *,
    tool_result_limit: int = DEFAULT_TOOL_RESULT_LIMIT,
) -> str:
    """Convert messages to flat text format for the summarizer LLM.

    Plain text — NOT chat format — so the model treats it as input to summarize
    instead of trying to continue the conversation. Tool results are truncated
    to `tool_result_limit` chars to keep the request size bounded. Secrets get
    redacted.

    Per-Agent override (#82): bei riesen Sessions kann der Agent-Owner das
    Limit auf 500 setzen, dann passt der Dump auch bei sehr aktiven Tool-Loops
    noch ins Modell-Window.
    """
    lines: list[str] = []
    for m in messages:
        lines.extend(_render_message(m, tool_result_limit))
    return redact("\n".join(lines))


def _render_message(m: Message, tool_result_limit: int) -> list[str]:
    role = m.role
    content = m.content

    if role == "user":
        return _render_user(content, tool_result_limit)
    if role == "assistant":
        return _render_assistant(content)
    if role == "system":
        return [f"[System]: {_text(_text_or_dump(content))}"]
    if role == "compaction":
        return [f"[Earlier summary]: {_text(_text_or_dump(content))}"]
    return [f"[{role.title()}]: {_text(_text_or_dump(content))}"]


def _render_user(content: Any, tool_result_limit: int) -> list[str]:
    if isinstance(content, str):
        return [f"[User]: {_text(content)}"]
    if isinstance(content, list):
        out: list[str] = []
        text_parts = []
        for block in content:
            if not isinstance(block, dict):
                text_parts.append(_text(str(block)))
                continue
            btype = block.get("type")
            if btype == "tool_result":
                txt = _truncate(_tool_result_text(block.get("content", "")), tool_result_limit)
                tag = block.get("tool_use_id", "")[-8:]
                marker = " (error)" if block.get("is_error") else ""
                out.append(f"[Tool result {tag}{marker}]: {txt}")
            elif btype == "text":
                text_parts.append(_text(block.get("text", "")))
            elif btype in _MEDIA:
                text_parts.append(_media_placeholder(block))
            else:
                text_parts.append(_truncate(_text_or_dump(block), UNKNOWN_BLOCK_LIMIT))
        if text_parts:
            out.insert(0, f"[User]: {' '.join(text_parts).strip()}")
        return out
    return [f"[User]: {_text(_text_or_dump(content))}"]


def _render_assistant(content: Any) -> list[str]:
    if isinstance(content, str):
        return [f"[Assistant]: {_text(content)}"]
    if isinstance(content, list):
        out: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                out.append(f"[Assistant]: {_text(str(block))}")
                continue
            btype = block.get("type")
            if btype == "text":
                out.append(f"[Assistant]: {_text(block.get('text', ''))}")
            elif btype == "thinking":
                out.append(f"[Assistant thinking]: {_text(block.get('thinking', ''))}")
            elif btype == "tool_use":
                args = json.dumps(block.get("input", {}), ensure_ascii=False)
                args = _truncate(args, 400)
                out.append(f"[Assistant tool call]: {block.get('name', '?')}({args})")
            elif btype in _MEDIA:
                out.append(f"[Assistant]: {_media_placeholder(block)}")
            # Sonst (codex_reasoning, redacted_thinking …): interne/verschlüsselte Daten – weglassen.
        return out
    return [f"[Assistant]: {_text(_text_or_dump(content))}"]


_MEDIA = {"image": "Bild", "document": "Dokument", "audio": "Ton", "video": "Video", "file": "Datei"}


def _size(b64: str) -> str:
    """Größe der Originaldatei aus der base64-Länge, deutsch formatiert (2,7 MB)."""
    n = len(b64) * 3 // 4
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")
    return f"{max(1, n // 1024)} KB"


def _media_placeholder(block: dict) -> str:
    """Bild/PDF/… nie als Daten in die Zusammenfassung – nur ein kurzer Hinweis, was da war."""
    kind = _MEDIA.get(block.get("type", ""), "Datei")
    src = block.get("source") if isinstance(block.get("source"), dict) else {}
    parts: list[str] = []
    title = block.get("title") or block.get("name") or block.get("filename")
    if title:
        parts.append(str(title)[:200])
    if src.get("type") == "url" and src.get("url"):
        parts.append(str(src["url"])[:300])
    if src.get("media_type"):
        parts.append(str(src["media_type"])[:100])
    if isinstance(src.get("data"), str):
        parts.append(_size(src["data"]))
    return f"[{kind}: {', '.join(parts)}]" if parts else f"[{kind}]"


def _tool_result_text(content: Any) -> str:
    """Inhalt eines Tool-Ergebnisses: Text-Blöcke als Text, Medien als Hinweis (nicht als base64)."""
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif isinstance(b, dict) and b.get("type") in _MEDIA:
                parts.append(_media_placeholder(b))
            else:
                parts.append(_truncate(_text_or_dump(b), UNKNOWN_BLOCK_LIMIT))
        return "\n".join(parts)
    return _text_or_dump(content)


def _text(s: str) -> str:
    return _truncate(s, TEXT_BLOCK_LIMIT)


def _text_or_dump(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n…[gekürzt: {len(s) - limit} Zeichen]"
