"""Helper für Token-Counting aus Anthropic/LiteLLM-Responses.

Wird von Streaming- und Non-Streaming-Pfaden gleichermaßen genutzt.
Zentral hier um Drift zwischen den Pfaden zu vermeiden.
"""
from __future__ import annotations

from typing import Any


def empty_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }


def usage_dict(usage: Any) -> dict[str, int]:
    """Extrahiert Token-Counts aus einem Anthropic-Usage-Objekt.

    Anthropic verwendet die Felder `cache_creation_input_tokens` und
    `cache_read_input_tokens` — wir mappen sie auf kürzere Keys ohne
    `_input_`, weil die Persistenz-Schicht und Frontend so heißen.
    """
    if not usage:
        return empty_usage()
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


def usage_from_litellm(resp: Any) -> dict[str, int]:
    """LiteLLM normalisiert die Response auf OpenAI-Format —
    usage hat prompt_tokens/completion_tokens, nicht input/output.
    Cache-Tokens sind providerabhängig (cache_creation/cache_read leer für non-Anthropic)."""
    usage = getattr(resp, "usage", None)
    if not usage:
        return empty_usage()
    # OpenAI-Format: prompt_tokens + completion_tokens
    in_tok = getattr(usage, "prompt_tokens", 0) or 0
    out_tok = getattr(usage, "completion_tokens", 0) or 0
    # LiteLLM kann cache-Felder durchreichen wenn der Provider sie liefert
    cc = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    return {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cache_creation_tokens": cc,
        "cache_read_tokens": cr,
    }
