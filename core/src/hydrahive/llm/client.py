from __future__ import annotations

import json
import logging
import os
from typing import AsyncIterator

import litellm

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True

_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

# Anthropic requires these headers for OAuth token requests (sk-ant-oat01-...).
# LiteLLM incorrectly sends Bearer headers for oat-tokens, so we bypass it entirely.
_ANTHROPIC_OAUTH_HEADERS = {
    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,prompt-caching-2024-07-31",
    "user-agent": "claude-cli/2.1.62",
    "x-app": "cli",
}

# Anthropic requires this as the first system block for OAuth requests.
_ANTHROPIC_OAUTH_IDENTITY = [
    {"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}
]

# MiniMax bietet einen Anthropic-kompatiblen Endpoint an. Kanonischer Host
# api.minimax.io (Global Platform). api.minimaxi.com ist die China-Platform —
# nicht kreuzkompatibel.
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"


def _load_config() -> dict:
    if not settings.llm_config.exists():
        return {"providers": [], "default_model": ""}
    return json.loads(settings.llm_config.read_text())


def _apply_keys(config: dict) -> None:
    for p in config.get("providers", []):
        key = p.get("api_key", "")
        pid = p.get("id", "")
        if not key:
            continue
        env = _ENV_MAP.get(pid)
        if env:
            os.environ[env] = key


def _get_anthropic_key(config: dict) -> str:
    for p in config.get("providers", []):
        if p.get("id") == "anthropic":
            return p.get("api_key", "")
    return ""


def _get_minimax_key(config: dict) -> str:
    for p in config.get("providers", []):
        if p.get("id") == "minimax":
            return p.get("api_key", "")
    return ""


def _strip_provider_prefix(model: str) -> str:
    """Remove 'anthropic/' or 'minimax/' prefix for direct SDK calls."""
    for prefix in ("anthropic/", "minimax/"):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def is_minimax_model(model: str) -> bool:
    """MiniMax-Modelle erkennen — entweder 'minimax/'-Prefix oder 'MiniMax-' im Namen."""
    if model.startswith("minimax/"):
        return True
    bare = _strip_provider_prefix(model)
    return bare.lower().startswith("minimax-")


async def _anthropic_oauth_complete(
    token: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        api_key="",
        auth_token=token,
        timeout=300.0,
        default_headers=_ANTHROPIC_OAUTH_HEADERS,
    )
    resp = await client.messages.create(
        model=_strip_provider_prefix(model),
        system=_ANTHROPIC_OAUTH_IDENTITY,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.content[0].text


async def _minimax_complete(
    api_key: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=60.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    resp = await client.messages.create(
        model=_strip_provider_prefix(model),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.content[0].text


async def _anthropic_oauth_stream(
    token: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        api_key="",
        auth_token=token,
        timeout=300.0,
        default_headers=_ANTHROPIC_OAUTH_HEADERS,
    )
    async with client.messages.stream(
        model=_strip_provider_prefix(model),
        system=_ANTHROPIC_OAUTH_IDENTITY,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            yield text


def default_model() -> str:
    return _load_config().get("default_model", "")


async def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    cfg = _load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if is_minimax_model(target):
        minimax_key = _get_minimax_key(cfg)
        if not minimax_key:
            raise ValueError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
        return await _minimax_complete(minimax_key, messages, target, temperature, max_tokens)

    anthropic_key = _get_anthropic_key(cfg)
    is_claude = _strip_provider_prefix(target).startswith("claude-")
    if is_claude and anthropic_key.startswith("sk-ant-oat"):
        return await _anthropic_oauth_complete(anthropic_key, messages, target, temperature, max_tokens)

    _apply_keys(cfg)
    resp = await litellm.acompletion(
        model=target,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


async def stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    cfg = _load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    anthropic_key = _get_anthropic_key(cfg)
    is_claude = _strip_provider_prefix(target).startswith("claude-")
    if is_claude and anthropic_key.startswith("sk-ant-oat"):
        async for chunk in _anthropic_oauth_stream(anthropic_key, messages, target, temperature, max_tokens):
            yield chunk
        return

    _apply_keys(cfg)
    resp = await litellm.acompletion(
        model=target,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
