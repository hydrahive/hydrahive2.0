"""Direkter anthropic-SDK-Pfad für Claude-Modelle und MiniMax (anthropic-kompatibel).

Vorteile gegenüber LiteLLM für diese beiden:
- volle Anthropic-Features (Prompt-Caching, Extended Thinking, Image-Blocks,
  Citations, Tool-Streaming) ohne Übersetzungsverlust
- ein konsistenter Pfad für OAuth- + Plain-Bearer-Tokens
"""
from __future__ import annotations

from typing import AsyncIterator

_OAUTH_HEADERS = {
    "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,prompt-caching-2024-07-31",
    "user-agent": "claude-cli/2.1.62",
    "x-app": "cli",
}

_OAUTH_IDENTITY = [
    {"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."}
]

# api.minimax.io = Global Platform; api.minimaxi.com = China — nicht kreuzkompatibel.
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"

# Gültige effort-Stufen für den neuen output_config.effort-Pfad (Claude 4.6+).
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# Claude-Modelle mit adaptive thinking + output_config.effort (4.6 und neuer).
# Alle anderen (Claude 4.5/4.1/4.0/3.x, MiniMax) nutzen den Legacy-Pfad.
EFFORT_PARAM_MODELS = (
    "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-4-6",
    "claude-sonnet-5", "claude-fable-5",
)

# Legacy: Reasoning-Effort → extended_thinking budget_tokens (Claude 4.5/älter, MiniMax).
# Auswahl bewusst niedrig: high = 16k Tokens reicht für die meisten Tool-Loops.
EFFORT_TO_BUDGET = {"low": 1024, "medium": 4096, "high": 16384}


def _uses_effort_param(model: str) -> bool:
    """True für Claude 4.6+ (adaptive thinking + output_config.effort)."""
    bare = strip_provider_prefix(model)
    return any(bare.startswith(p) for p in EFFORT_PARAM_MODELS)


def apply_effort(kwargs: dict, model: str, effort: str | None) -> None:
    """Setzt Reasoning-Effort modellabhängig (mutiert kwargs in-place).

    Neuer Pfad (Claude 4.6+): output_config.effort (low..max) + thinking.adaptive.
    temperature/max_tokens bleiben unangetastet — der deprecated-temperature-Retry
    im Call-Layer kümmert sich darum.

    Legacy-Pfad (Claude 4.5/älter, MiniMax): extended_thinking budget_tokens
    (nur low/medium/high), temperature=1.0, max_tokens hochgezogen.

    Bei effort=None/leer oder unbekanntem Wert: kein-op.
    """
    if not effort:
        return
    if _uses_effort_param(model):
        if effort not in EFFORT_LEVELS:
            return
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs.setdefault("output_config", {})["effort"] = effort
        return
    budget = EFFORT_TO_BUDGET.get(effort)
    if budget is None:
        return
    kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
    if kwargs.get("max_tokens", 0) <= budget:
        kwargs["max_tokens"] = budget + 4096
    kwargs["temperature"] = 1.0


def strip_provider_prefix(model: str) -> str:
    """Removes 'anthropic/' or 'minimax/' prefix for direct SDK calls."""
    for prefix in ("anthropic/", "minimax/"):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def extract_text(content) -> str:
    """Joined alle Text-Blocks aus einer Anthropic-SDK-Response.
    Skipped ThinkingBlocks (haben kein .text bei Extended Thinking / MiniMax)."""
    parts = [getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text"]
    return "".join(parts)


def is_minimax_model(model: str) -> bool:
    if model.startswith("minimax/"):
        return True
    return strip_provider_prefix(model).lower().startswith("minimax-")


def convert_images_for_minimax(messages: list[dict]) -> list[dict]:
    """Anthropic image blocks → OpenAI image_url blocks für MiniMax.

    MiniMax's /anthropic Endpoint übergibt Anthropic-Image-Blöcke nicht ans Modell.
    Das Modell erwartet intern OpenAI-Format: {type:"image_url",image_url:{url:"data:..."}}.
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


def _client(key: str):
    """Anthropic-SDK-Client. OAuth-Tokens brauchen auth_token + Identity-Header,
    Plain-API-Keys brauchen api_key. Beide gehen über das gleiche SDK."""
    import anthropic as _anthropic
    if key.startswith("sk-ant-oat"):
        return _anthropic.AsyncAnthropic(
            api_key="", auth_token=key, timeout=300.0,
            default_headers=_OAUTH_HEADERS,
        ), True
    return _anthropic.AsyncAnthropic(api_key=key, timeout=300.0), False


def _is_temperature_deprecated_error(exc: Exception) -> bool:
    """True wenn Anthropic mit 'temperature is deprecated for this model' 400t.

    Manche neueren Claude-Modelle (z.B. opus-4-7+, sonnet-5) akzeptieren keinen
    temperature-Parameter mehr. Gilt für alle direkten Anthropic-SDK-Pfade
    (complete/stream, OAuth/API-Key/MiniMax) — nicht nur den Runner-Pfad.
    """
    msg = str(exc).lower()
    return "temperature" in msg and "deprecated" in msg


async def anthropic_complete(
    key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> str:
    client, is_oauth = _client(key)
    # Anthropic-API erlaubt keine role="system" in messages — als top-level system extrahieren
    system_texts = [m["content"] for m in messages if m.get("role") == "system"]
    user_messages = [m for m in messages if m.get("role") != "system"]
    system: str | list | None = "\n\n".join(system_texts) if system_texts else None
    if is_oauth:
        system = _OAUTH_IDENTITY  # OAuth-Identity überschreibt (ist eine Liste)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": user_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system
    from hydrahive.llm._oauth_usage import extract_rate_limit_headers
    import anthropic as _anthropic

    try:
        raw_resp = await client.messages.with_raw_response.create(**kwargs)
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        raw_resp = await client.messages.with_raw_response.create(**kwargs)
    extract_rate_limit_headers(raw_resp.headers)
    resp = raw_resp.parse()
    return extract_text(resp.content)


async def minimax_complete(
    api_key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> str:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=60.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = await client.messages.create(**kwargs)
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        resp = await client.messages.create(**kwargs)
    return extract_text(resp.content)


async def minimax_stream(
    api_key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> AsyncIterator[str]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=60.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        async with client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield text
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        async with client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield text


async def anthropic_stream(
    key: str, messages: list[dict], model: str,
    temperature: float, max_tokens: int,
) -> AsyncIterator[str]:
    import anthropic as _anthropic

    client, is_oauth = _client(key)
    kwargs: dict = {
        "model": strip_provider_prefix(model),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if is_oauth:
        kwargs["system"] = _OAUTH_IDENTITY
    try:
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
    except _anthropic.BadRequestError as e:
        if not _is_temperature_deprecated_error(e):
            raise
        kwargs.pop("temperature", None)
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
