"""Anthropic + MiniMax + LiteLLM backend calls for llm_bridge."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.llm import client as llm_client
from hydrahive.runner._litellm_convert import (
    messages_to_openai,
    openai_response_to_anthropic_blocks,
    openai_stop_to_anthropic,
    tools_to_openai,
)


def _cache_control(ttl: str) -> dict:
    ctrl: dict[str, Any] = {"type": "ephemeral"}
    if ttl and ttl != "5m":
        ctrl["ttl"] = ttl
    return ctrl


def _block_to_dict(block: Any) -> dict:
    """Anthropic SDK returns typed objects; normalize to plain dicts for DB-storage."""
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if hasattr(block, "dict"):
        return block.dict()
    if isinstance(block, dict):
        return block
    return json.loads(json.dumps(block, default=lambda o: getattr(o, "__dict__", str(o))))


async def anthropic_call(
    *,
    key: str,
    model: str,
    system_prompt: str,
    volatile_system: str | None = None,
    cache_ttl: str = "1h",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict], str]:
    import anthropic as _anthropic
    is_oauth = key.startswith("sk-ant-oat")
    if is_oauth:
        client = _anthropic.AsyncAnthropic(
            api_key="", auth_token=key, timeout=300.0,
            default_headers=llm_client._ANTHROPIC_OAUTH_HEADERS,
        )
    else:
        client = _anthropic.AsyncAnthropic(api_key=key, timeout=300.0)

    system_blocks: list[dict[str, Any]] = []
    if is_oauth:
        system_blocks.append({"type": "text", "text": llm_client._ANTHROPIC_OAUTH_IDENTITY[0]["text"]})
    if system_prompt:
        system_blocks.append({"type": "text", "text": system_prompt, "cache_control": _cache_control(cache_ttl)})
    elif system_blocks:
        system_blocks[0]["cache_control"] = _cache_control(cache_ttl)
    if volatile_system:
        system_blocks.append({"type": "text", "text": volatile_system})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_blocks:
        kwargs["system"] = system_blocks
    if tools:
        cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
        kwargs["tools"] = cached_tools

    # Manche neueren Claude-Modelle (z.B. opus-4-7) akzeptieren kein temperature
    # mehr — Anthropic returnt dann 400 "temperature is deprecated for this
    # model". Wenn das passiert: einmal ohne temperature retry.
    try:
        resp = await client.messages.create(**kwargs)
    except _anthropic.BadRequestError as e:
        if "temperature" in str(e).lower() and "deprecated" in str(e).lower():
            kwargs.pop("temperature", None)
            resp = await client.messages.create(**kwargs)
        else:
            raise
    blocks = [_block_to_dict(b) for b in resp.content]
    stop_reason = getattr(resp, "stop_reason", "") or ""
    return blocks, stop_reason


async def minimax_anthropic_call(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    volatile_system: str | None = None,
    cache_ttl: str = "1h",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict], str]:
    """Direkter Anthropic-SDK-Call gegen api.minimax.io/anthropic.

    Unterschiede zu OAuth:
    - base_url auf MiniMax
    - api_key direkt (kein OAuth-Token)
    - Authorization: Bearer manuell gesetzt (MiniMax-Konvention)
    - kein Identity-System-Block — MiniMax erwartet den nicht
    """
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=llm_client.MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=300.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_prompt or volatile_system:
        blocks: list[dict[str, Any]] = []
        if system_prompt:
            blocks.append({"type": "text", "text": system_prompt, "cache_control": _cache_control(cache_ttl)})
        if volatile_system:
            blocks.append({"type": "text", "text": volatile_system})
        kwargs["system"] = blocks
    if tools:
        cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
        kwargs["tools"] = cached_tools

    resp = await client.messages.create(**kwargs)
    blocks = [_block_to_dict(b) for b in resp.content]
    stop_reason = getattr(resp, "stop_reason", "") or ""
    return blocks, stop_reason


def _is_tool_use_unsupported(exc: Exception) -> bool:
    """Erkennt Provider-Fehler 'dieses Modell unterstützt kein Tool-Use'.

    Beispiel NVIDIA NIM:
      400 - {'error': 'Tool use has not been enabled, because it is unsupported by ...'}
    OpenRouter / andere können andere Wortwahl haben — wir matchen tolerant.
    """
    msg = str(exc).lower()
    if "tool use" in msg or "tool_use" in msg or "function calling" in msg or "tools" in msg:
        if any(k in msg for k in ("unsupported", "not enabled", "not supported",
                                   "doesn't support", "does not support", "unavailable")):
            return True
    return False


async def litellm_call(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict], str]:
    """Tool-Loop-fähiger Call für alle non-Anthropic/non-MiniMax Provider via LiteLLM.

    Unterstützt Provider die OpenAI-kompatibles Function-Calling können:
    OpenAI selbst, NVIDIA NIM, Groq, Mistral, Gemini, OpenRouter usw.

    Konvertiert HH2-internes Anthropic-Format in OpenAI-Format, ruft LiteLLM,
    konvertiert Antwort zurück.

    Bei Modellen ohne Tool-Use-Support (z.B. qwen2.5-coder auf NVIDIA): erneut
    OHNE tools versuchen — das Modell antwortet dann als reiner Chat.

    LiteLLM liest Provider-API-Keys aus den ENV-Variablen die _config.apply_keys()
    setzt — der Aufrufer muss apply_keys vor dem Call ausgeführt haben.
    """
    import logging
    import litellm

    logger = logging.getLogger(__name__)

    oai_messages = messages_to_openai(messages, system_prompt)
    oai_tools = tools_to_openai(tools)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": oai_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": 120,  # manche NVIDIA-NIM-Modelle hängen mit tools-Schema, hard-cap
    }
    if oai_tools:
        kwargs["tools"] = oai_tools
        kwargs["tool_choice"] = "auto"

    try:
        resp = await litellm.acompletion(**kwargs)
    except Exception as e:
        if oai_tools and _is_tool_use_unsupported(e):
            logger.warning("Modell %s unterstützt kein Tool-Use — retry ohne tools (Agent kann keine "
                           "Tools aufrufen, antwortet nur als Chat)", model)
            kwargs.pop("tools", None)
            kwargs.pop("tool_choice", None)
            resp = await litellm.acompletion(**kwargs)
        else:
            raise

    choice = resp.choices[0]
    blocks = openai_response_to_anthropic_blocks(choice.message)
    stop_reason = openai_stop_to_anthropic(getattr(choice, "finish_reason", "") or "")
    return blocks, stop_reason
