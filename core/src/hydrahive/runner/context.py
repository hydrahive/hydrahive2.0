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
    "tool_use": {"type", "id", "name", "input"},
    "thinking": {"type", "thinking", "signature"},
    "tool_result": {"type", "tool_use_id", "content", "is_error"},
}


def _sanitize_block(b: Any) -> Any:
    """Strip SDK-only fields (parsed_output, caller, citations) the API rejects."""
    if not isinstance(b, dict):
        return b
    btype = b.get("type", "")
    allowed = _ANTHROPIC_ALLOWED.get(btype)
    if allowed is None:
        return b
    return {k: v for k, v in b.items() if k in allowed}


def _normalize_content(content: Any) -> Any:
    """Pass through strings; sanitize Anthropic-shaped content lists."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return [_sanitize_block(b) for b in content]
    if isinstance(content, dict):
        return [_sanitize_block(content)]
    return str(content)


def merge_text_blocks(blocks: list[dict]) -> str:
    """Concatenate all text blocks for display/logging."""
    parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(p for p in parts if p)


def extract_tool_uses(blocks: list[dict]) -> list[dict]:
    """Filter assistant content to just tool_use blocks."""
    return [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
