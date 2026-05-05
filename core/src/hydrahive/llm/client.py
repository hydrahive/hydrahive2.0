"""LLM-Client-Public-API: complete(), stream(), default_model().

Routing:
- MiniMax-Modelle → anthropic-SDK gegen api.minimax.io/anthropic (siehe _anthropic.py)
- Claude-Modelle → anthropic-SDK direkt (OAuth oder Plain-Bearer)
- Alle anderen (OpenAI/OpenRouter/Groq/Mistral/Gemini/NVIDIA) → LiteLLM
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

import litellm

from hydrahive.llm import _anthropic
from hydrahive.llm import _config
from hydrahive.llm._anthropic import (
    anthropic_complete,
    anthropic_stream,
    convert_images_for_minimax,
    is_minimax_model,
    minimax_complete,
    minimax_stream,
    strip_provider_prefix,
)
from hydrahive.llm._config import apply_keys, get_provider_key, load_config

logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True

# Backwards-Compat-Re-Exports für runner/llm_bridge*.py, voice/tts.py,
# agents/_validation.py — die greifen mit Underscore-Namen direkt auf
# private Helpers zu. Statt 4 Files anzufassen werden die Symbole hier
# als Aliase gespiegelt. Tatsächliche Definitionen liegen in _config.py
# bzw. _anthropic.py.
_load_config = load_config
_apply_keys = apply_keys
_strip_provider_prefix = strip_provider_prefix
_ENV_MAP = _config._ENV_MAP
_ANTHROPIC_OAUTH_HEADERS = _anthropic._OAUTH_HEADERS
_ANTHROPIC_OAUTH_IDENTITY = _anthropic._OAUTH_IDENTITY
MINIMAX_BASE_URL = _anthropic.MINIMAX_BASE_URL


def _get_anthropic_key(cfg: dict) -> str:
    return get_provider_key(cfg, "anthropic")


def _get_minimax_key(cfg: dict) -> str:
    return get_provider_key(cfg, "minimax")


__all__ = [
    "complete", "stream", "default_model",
    "is_minimax_model", "convert_images_for_minimax",
]


def default_model() -> str:
    return load_config().get("default_model", "")


async def complete(
    messages: list[dict], model: str | None = None,
    temperature: float = 0.7, max_tokens: int = 4096,
) -> str:
    cfg = load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if is_minimax_model(target):
        key = get_provider_key(cfg, "minimax")
        if not key:
            raise ValueError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
        return await minimax_complete(key, messages, target, temperature, max_tokens)

    if strip_provider_prefix(target).startswith("claude-"):
        from hydrahive.oauth.anthropic import resolve_anthropic_token
        key = await resolve_anthropic_token()
        if not key:
            raise ValueError("Anthropic-Auth fehlt — API-Key oder OAuth-Login auf der LLM-Seite")
        return await anthropic_complete(key, messages, target, temperature, max_tokens)

    apply_keys(cfg)
    resp = await litellm.acompletion(
        model=target, messages=messages,
        temperature=temperature, max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


async def stream(
    messages: list[dict], model: str | None = None,
    temperature: float = 0.7, max_tokens: int = 4096,
) -> AsyncIterator[str]:
    cfg = load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if is_minimax_model(target):
        key = get_provider_key(cfg, "minimax")
        if not key:
            raise ValueError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
        async for chunk in minimax_stream(key, messages, target, temperature, max_tokens):
            yield chunk
        return

    if strip_provider_prefix(target).startswith("claude-"):
        from hydrahive.oauth.anthropic import resolve_anthropic_token
        key = await resolve_anthropic_token()
        if not key:
            raise ValueError("Anthropic-Auth fehlt — API-Key oder OAuth-Login auf der LLM-Seite")
        async for chunk in anthropic_stream(key, messages, target, temperature, max_tokens):
            yield chunk
        return

    apply_keys(cfg)
    resp = await litellm.acompletion(
        model=target, messages=messages,
        temperature=temperature, max_tokens=max_tokens, stream=True,
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
