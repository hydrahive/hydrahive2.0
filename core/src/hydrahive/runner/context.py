from __future__ import annotations

from typing import Any

from hydrahive.db.messages import Message


def heal_orphan_tool_uses(history: list[Message]) -> list[Message]:
    """Anthropic API requires every tool_use in an assistant message to be
    immediately followed by tool_result blocks in the next user message.
    If history is broken (e.g. previous turn aborted on max_tokens before
    persisting tool_results), inject synthetic results for the LLM call.

    Returns a (potentially new) list. Does NOT mutate the DB.
    """
    out: list[Message] = []
    i = 0
    while i < len(history):
        msg = history[i]
        out.append(msg)
        if msg.role == "assistant" and isinstance(msg.content, list):
            tool_uses = [b for b in msg.content if isinstance(b, dict) and b.get("type") == "tool_use"]
            if tool_uses:
                next_msg = history[i + 1] if i + 1 < len(history) else None
                existing_ids: set[str] = set()
                if next_msg and next_msg.role == "user" and isinstance(next_msg.content, list):
                    existing_ids = {
                        b.get("tool_use_id") for b in next_msg.content
                        if isinstance(b, dict) and b.get("type") == "tool_result"
                    }
                missing = [tu for tu in tool_uses if tu.get("id") not in existing_ids]
                if missing:
                    synthetic_blocks = [
                        {
                            "type": "tool_result",
                            "tool_use_id": tu.get("id", ""),
                            "content": "Abgebrochen: kein Resultat aufgezeichnet (Truncation im vorigen Turn)",
                            "is_error": True,
                        }
                        for tu in missing
                    ]
                    if next_msg and next_msg.role == "user" and isinstance(next_msg.content, list):
                        healed = Message(
                            id=next_msg.id, session_id=next_msg.session_id, role="user",
                            content=list(next_msg.content) + synthetic_blocks,
                            created_at=next_msg.created_at, token_count=next_msg.token_count,
                            metadata=next_msg.metadata,
                        )
                        out.append(healed)
                        i += 2
                        continue
                    synthetic = Message(
                        id=f"synthetic-{i}", session_id=msg.session_id, role="user",
                        content=synthetic_blocks, created_at=msg.created_at,
                        token_count=None, metadata={},
                    )
                    out.append(synthetic)
        i += 1
    return out


def to_anthropic_messages(history: list[Message]) -> list[dict]:
    """Convert our DB-message history to Anthropic API format.

    Our DB stores:
      role='user'      content=str | list[tool_result blocks]
      role='assistant' content=list[text/tool_use blocks] | str
      role='tool'      (legacy/alternative — converted to user with tool_result)

    Anthropic expects:
      role='user'|'assistant', content=str | list[content blocks]

    System messages are NOT included here (passed separately to messages.create).
    """
    out: list[dict] = []
    for m in history:
        if m.role == "system":
            continue
        role = "user" if m.role in ("user", "tool") else "assistant"
        content = _normalize_content(m.content)
        if content == "" or content == []:
            continue
        out.append({"role": role, "content": content})
    return out


_ANTHROPIC_ALLOWED = {
    "text": {"type", "text"},
    "image": {"type", "source"},
    "tool_use": {"type", "id", "name", "input"},
    "tool_result": {"type", "tool_use_id", "content", "is_error"},
}

# Block-Typen die NIE zurück an die LLM-API geschickt werden dürfen.
# - thinking: Extended-Thinking-Blöcke kommen von Anthropic (oder MiniMax als
#   internal thinking) mit einer Signature. Wenn wir die zurückschicken ohne
#   den Extended-Thinking-Mode im aktuellen Call zu aktivieren, weist die API
#   das mit "Invalid signature in thinking block" (400) ab. Wir nutzen Extended-
#   Thinking nicht aktiv → komplett strippen aus der History (#79).
_BLOCKS_TO_STRIP: frozenset[str] = frozenset({"thinking"})


def _sanitize_block(b: Any) -> Any | None:
    """Strip SDK-only fields die API rejects. Returns None für strip-Blöcke."""
    if not isinstance(b, dict):
        return b
    btype = b.get("type", "")
    if btype in _BLOCKS_TO_STRIP:
        return None
    allowed = _ANTHROPIC_ALLOWED.get(btype)
    if allowed is None:
        return b
    return {k: v for k, v in b.items() if k in allowed}


def _normalize_content(content: Any) -> Any:
    """Pass through strings; sanitize Anthropic-shaped content lists.
    None-Werte aus _sanitize_block werden rausgefiltert."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return [b for b in (_sanitize_block(x) for x in content) if b is not None]
    if isinstance(content, dict):
        sanitized = _sanitize_block(content)
        return [sanitized] if sanitized is not None else []
    return str(content)


def merge_text_blocks(blocks: list[dict]) -> str:
    """Concatenate all text blocks for display/logging."""
    parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(p for p in parts if p)


def extract_tool_uses(blocks: list[dict]) -> list[dict]:
    """Filter assistant content to just tool_use blocks."""
    return [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
