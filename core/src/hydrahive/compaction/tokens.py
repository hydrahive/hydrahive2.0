from __future__ import annotations

import json
from typing import Any

# Char-based estimate. Real tokens vary by model — Anthropic ~3.5 chars/token
# for English/code, more for German. Use 4 as a conservative-ish average.
# We always overestimate slightly to trigger compaction earlier rather than
# blowing through the context window.
_CHARS_PER_TOKEN = 3.5

# Bei serialisierten History-Dumps (viel JSON, tool_use mit dichten Argumenten,
# strukturierter Text) ist 1 Token oft nur 1-1.5 Zeichen. Anthropic-Tokenizer
# rechnet bei einem 2.1MB-Dump 1.83M Tokens (≈ 1.15 chars/token). Wir nutzen
# 1.2 als sehr konservatives Estimate für Compaction-Decisions damit Chunking
# zuverlässig greift bevor das Modell 400 wirft.
_CHARS_PER_TOKEN_DENSE = 1.2


def estimate_text(text: str) -> int:
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def estimate_dense_text(text: str) -> int:
    """Konservatives Estimate für serialisierte/strukturierte Dumps. Liefert
    deutlich höhere Token-Counts als estimate_text — geeignet für Pre-Flight-
    Checks die das echte Modell-Limit nicht überschreiten dürfen."""
    return max(1, int(len(text) / _CHARS_PER_TOKEN_DENSE))


def estimate_message_content(content: Any) -> int:
    """Estimate tokens for the content field of a Message — string or block-list."""
    if content is None:
        return 0
    if isinstance(content, str):
        return estimate_text(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                # Cheap: serialize and estimate. Avoids type-specific code.
                total += estimate_text(json.dumps(block, ensure_ascii=False))
            else:
                total += estimate_text(str(block))
        return total
    if isinstance(content, dict):
        return estimate_text(json.dumps(content, ensure_ascii=False))
    return estimate_text(str(content))


def estimate_message(message: Any) -> int:
    """Estimate tokens for one DB Message — uses cached token_count if present."""
    if hasattr(message, "token_count") and message.token_count:
        return message.token_count
    return estimate_message_content(getattr(message, "content", None))


def context_window_for(model: str) -> int:
    """Approximate context window in tokens for known models."""
    m = model.lower()
    # Spezielle Versionen mit größerem Window — vor den generischen Patterns prüfen
    if "claude-opus-4-7" in m:
        return 1_000_000  # Opus 4-7 hat 1M Window (verifiziert via Fehlermeldung)
    if "claude-sonnet-4" in m or "claude-opus-4" in m:
        return 200_000
    if "claude-haiku-4" in m:
        return 200_000
    if "claude-3-7" in m or "claude-3-5" in m:
        return 200_000
    if "gpt-4" in m or "gpt-4o" in m:
        return 128_000
    if "gemini" in m:
        return 1_000_000
    if "minimax" in m:
        return 256_000
    if "deepseek" in m:
        return 128_000
    if "llama" in m or "mistral" in m or "mixtral" in m:
        return 128_000
    # qwen ist nicht uniform — manche Varianten haben nur 32k, andere 256k
    if "qwen" in m:
        # qwen2.5-coder (32b/7b/14b) hat 32k, qwen2.5 generisch 32k
        if "qwen2.5-coder" in m or "qwen2.5" in m:
            return 32_000
        # qwen3, qwen3-next, qwen3-coder, qwen3.5 haben 256k
        if "qwen3" in m:
            return 262_144
        return 32_000  # unbekannte qwen-Variante: konservativ
    return 32_000  # safe default
