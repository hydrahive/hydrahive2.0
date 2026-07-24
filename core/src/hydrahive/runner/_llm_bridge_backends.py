"""Anthropic + MiniMax + LiteLLM backend calls for llm_bridge."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from hydrahive.llm import client as llm_client
from hydrahive.runner._anthropic_payload import (
    block_to_dict as _block_to_dict,
    build_anthropic_kwargs,
    build_minimax_kwargs,
)
from hydrahive.runner._litellm_convert import (
    messages_to_openai,
    openai_response_to_anthropic_blocks,
    openai_stop_to_anthropic,
    tools_to_openai,
)


async def anthropic_call(
    *,
    key: str,
    model: str,
    system_prompt: str,
    volatile_system: str | None = None,
    summary_system: str | None = None,
    cache_ttl: str = "5m",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
) -> tuple[list[dict], str, dict[str, int]]:
    import anthropic as _anthropic
    from hydrahive.runner._token_usage import usage_dict

    client, kwargs = build_anthropic_kwargs(
        key=key, model=model, system_prompt=system_prompt,
        volatile_system=volatile_system, summary_system=summary_system,
        cache_ttl=cache_ttl, messages=messages, tools=tools,
        temperature=temperature, max_tokens=max_tokens, reasoning_effort=reasoning_effort,
    )

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
    return blocks, stop_reason, usage_dict(getattr(resp, "usage", None))


async def minimax_anthropic_call(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    volatile_system: str | None = None,
    summary_system: str | None = None,
    cache_ttl: str = "5m",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
) -> tuple[list[dict], str, dict[str, int]]:
    """Direkter Anthropic-SDK-Call gegen api.minimax.io/anthropic.

    Unterschiede zu OAuth:
    - base_url auf MiniMax
    - api_key direkt (kein OAuth-Token)
    - Authorization: Bearer manuell gesetzt (MiniMax-Konvention)
    - kein Identity-System-Block — MiniMax erwartet den nicht
    """
    from hydrahive.runner._token_usage import usage_dict

    client, kwargs = build_minimax_kwargs(
        api_key=api_key, model=model, system_prompt=system_prompt,
        volatile_system=volatile_system, summary_system=summary_system,
        messages=messages, tools=tools, temperature=temperature,
        max_tokens=max_tokens, reasoning_effort=reasoning_effort,
    )

    logger.debug(
        "MiniMax non-stream: model=%s msgs=%d sys_len=%d tools=%d thinking=%s",
        model, len(kwargs.get("messages", [])),
        len(kwargs.get("system", "") or ""),
        len(kwargs.get("tools", [])),
        "thinking" in kwargs,
    )
    resp = await client.messages.create(**kwargs)
    blocks = [_block_to_dict(b) for b in resp.content]
    stop_reason = getattr(resp, "stop_reason", "") or ""
    return blocks, stop_reason, usage_dict(getattr(resp, "usage", None))


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
    api_base: str | None = None,
    num_ctx: int | None = None,
) -> tuple[list[dict], str, dict[str, int]]:
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
    # User-eigener Endpoint (Ollama, LM Studio, vLLM …). Nur setzen wenn gegeben,
    # damit Cloud-Provider ihr Default-Routing behalten.
    if api_base:
        kwargs["api_base"] = api_base
    # num_ctx nur für Ollama: das Modell-Kontextfenster explizit anfordern, sonst
    # deckelt Ollama lokal auf 4096 und schneidet größere Prompts ab (-> falscher
    # Kontext + Dauer-Compact). num_ctx ist eine Ollama-Option; LiteLLM reicht sie
    # über extra_body.options an den nativen Ollama-Endpoint durch.
    if num_ctx and model.startswith("ollama/"):
        kwargs["num_ctx"] = num_ctx
        kwargs["extra_body"] = {"options": {"num_ctx": num_ctx}}

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

    from hydrahive.runner._token_usage import usage_from_litellm

    choice = resp.choices[0]
    blocks = openai_response_to_anthropic_blocks(choice.message)
    stop_reason = openai_stop_to_anthropic(getattr(choice, "finish_reason", "") or "")
    return blocks, stop_reason, usage_from_litellm(resp)
