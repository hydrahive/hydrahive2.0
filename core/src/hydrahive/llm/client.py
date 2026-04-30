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
    "nvidia": "NVIDIA_NIM_API_KEY",
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


def convert_images_for_minimax(messages: list[dict]) -> list[dict]:
    """Anthropic image blocks → OpenAI image_url blocks für MiniMax.

    MiniMax's /anthropic Endpoint übergibt Anthropic-Image-Blöcke nicht ans Modell.
    Das Modell erwartet intern OpenAI-Format: {"type":"image_url","image_url":{"url":"data:..."}}.
    """
    result = []
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            new_content = []
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "image":
                    source = b.get("source") or {}
                    data = source.get("data", "")
                    mime = source.get("media_type") or "image/png"
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"},
                    })
                else:
                    new_content.append(b)
            result.append({**m, "content": new_content})
        else:
            result.append(m)
    return result


_config_cache: tuple[float, dict] | None = None


def _load_config() -> dict:
    """LLM-Config laden mit mtime-basiertem Cache.

    Bei jedem Anthropic-Call wurde die Config-Datei neu eingelesen — bei vielen
    parallelen Streams summiert sich das. mtime-Check ist billig und invalidiert
    nur wenn die Datei tatsächlich geändert wurde (z.B. nach LLM-Page-Save).
    """
    global _config_cache
    path = settings.llm_config
    if not path.exists():
        return {"providers": [], "default_model": ""}
    mtime = path.stat().st_mtime
    if _config_cache and _config_cache[0] == mtime:
        return _config_cache[1]
    data = json.loads(path.read_text())
    _config_cache = (mtime, data)
    return data


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


def _extract_text(content) -> str:
    """Join all text blocks from an Anthropic-SDK response.

    MiniMax (and Anthropic with extended thinking) can return ThinkingBlock
    items in content[]. Those have no .text attribute. We iterate and pick
    only the actual text blocks.
    """
    parts = [getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text"]
    return "".join(parts)


def is_minimax_model(model: str) -> bool:
    """MiniMax-Modelle erkennen — entweder 'minimax/'-Prefix oder 'MiniMax-' im Namen."""
    if model.startswith("minimax/"):
        return True
    bare = _strip_provider_prefix(model)
    return bare.lower().startswith("minimax-")


def _anthropic_client(key: str):
    """Anthropic-SDK-Client. OAuth-Tokens (sk-ant-oat...) brauchen
    auth_token + Identity-Header, Plain-API-Keys (sk-ant-api...)
    brauchen api_key. Beide gehen über das gleiche SDK."""
    import anthropic as _anthropic
    if key.startswith("sk-ant-oat"):
        return _anthropic.AsyncAnthropic(
            api_key="", auth_token=key, timeout=300.0,
            default_headers=_ANTHROPIC_OAUTH_HEADERS,
        ), True
    return _anthropic.AsyncAnthropic(api_key=key, timeout=300.0), False


async def _anthropic_complete(
    key: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    client, is_oauth = _anthropic_client(key)
    kwargs: dict = {
        "model": _strip_provider_prefix(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if is_oauth:
        kwargs["system"] = _ANTHROPIC_OAUTH_IDENTITY
    resp = await client.messages.create(**kwargs)
    return _extract_text(resp.content)


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
    return _extract_text(resp.content)


async def _anthropic_stream(
    key: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    client, is_oauth = _anthropic_client(key)
    kwargs: dict = {
        "model": _strip_provider_prefix(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if is_oauth:
        kwargs["system"] = _ANTHROPIC_OAUTH_IDENTITY
    async with client.messages.stream(**kwargs) as stream:
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

    # Anthropic Claude → direkt via anthropic-SDK (sowohl OAuth als auch Plain-Bearer).
    # Vorteile gegenüber LiteLLM: volle Anthropic-Features (Prompt-Caching,
    # Extended Thinking, Image-Blocks, Citations, Tool-Streaming) ohne
    # LiteLLM-Übersetzungsverlust + ein konsistenter Pfad statt zwei.
    if _strip_provider_prefix(target).startswith("claude-"):
        anthropic_key = _get_anthropic_key(cfg)
        if not anthropic_key:
            raise ValueError("Anthropic-API-Key fehlt — Provider 'anthropic' in der LLM-Config setzen")
        return await _anthropic_complete(anthropic_key, messages, target, temperature, max_tokens)

    # Alle anderen Provider (OpenAI, OpenRouter, Groq, Mistral, Gemini, NVIDIA-NIM)
    # über LiteLLM — da macht es seinen Job als echte Provider-Abstraktion.
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

    # Anthropic Claude → direktes anthropic-SDK (siehe complete() für Begründung).
    if _strip_provider_prefix(target).startswith("claude-"):
        anthropic_key = _get_anthropic_key(cfg)
        if not anthropic_key:
            raise ValueError("Anthropic-API-Key fehlt")
        async for chunk in _anthropic_stream(anthropic_key, messages, target, temperature, max_tokens):
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
