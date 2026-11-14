"""Hilfen für den LLM-Aufruf: Werkzeug-Gate je Modell und Bereinigung der Antwort-Blöcke."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ALLOWED_FIELDS = {
    "text": {"type", "text"},
    "tool_use": {"type", "id", "name", "input"},
    "thinking": {"type", "thinking", "signature"},
    "tool_result": {"type", "tool_use_id", "content", "is_error"},
    # Opaque provider state only; never rendered. Required for stateless Codex
    # reasoning continuity and prompt-cache efficiency.
    "codex_reasoning": {"type", "encrypted_content", "model"},
}


def sanitize_blocks(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for b in blocks:
        btype = b.get("type", "")
        allowed = _ALLOWED_FIELDS.get(btype)
        if allowed is None:
            out.append(b)
            continue
        out.append({k: v for k, v in b.items() if k in allowed})
    return out


def tools_for(model: str, tools: list[dict]) -> list[dict]:
    """Tools nur an Modelle geben, die Function-Calling können.

    Modelle ohne Tool-Support erfinden sonst Tool-Calls als Text-JSON, das wir
    (korrekt) nicht ausführen — es landet stumpf im Chat. Das Gate greift PRO
    MODELL, weil die Fallback-Kette auf ein Modell mit anderer Fähigkeit
    wechseln kann. Die übergebene Liste wird nie mutiert.
    """
    if not tools:
        return tools
    from hydrahive.llm.tool_support import model_supports_tools
    if model_supports_tools(model):
        return tools
    logger.info(
        "Modell %s kann kein Function-Calling — %d Tool-Schemas werden nicht gesendet",
        model, len(tools),
    )
    return []
