"""Text fürs Embedding auf das Token-Limit kürzen (Task 36caf245).

Vorher wurde nach Zeichen gekürzt (24.000, Annahme „~6000 Tokens“). Gemessen 09.10.2026: ein tool_call mit
24.000 Zeichen = 9.644 Tokens > 8.192 (Limit text-embedding-3-small) → OpenAI lehnte das ganze 32er-Paket ab,
der Nachtrag hing dauerhaft. Jetzt: nach Tokens kürzen (cl100k_base, Tokenizer der OpenAI-Embedding-Modelle).
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

MAX_TOKENS = 8000            # Puffer unter 8.192
FALLBACK_CHARS = 12_000      # ohne Tokenizer: 24.000 Zeichen waren schon zu viel → halbiert (≥ 1,5 Zeichen/Token)


@lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception as e:  # noqa: BLE001 — Tokenizer fehlt/offline: vorsichtig nach Zeichen kürzen
        logger.warning("Tokenizer nicht verfügbar (%s) – kürze Embedding-Texte nach Zeichen", e)
        return None


def clip_for_embedding(text: str, max_tokens: int = MAX_TOKENS) -> str:
    """Höchstens ``max_tokens`` Tokens. Kurze Texte (≤ max_tokens Zeichen) gehen ohne Zählen durch."""
    if not text or len(text) <= max_tokens:
        return text
    enc = _encoder()
    if enc is None:
        return text[:FALLBACK_CHARS]
    toks = enc.encode(text, disallowed_special=())
    if len(toks) <= max_tokens:
        return text
    return enc.decode(toks[:max_tokens])
