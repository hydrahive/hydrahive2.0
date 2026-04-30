from __future__ import annotations

import json
import logging
from typing import Any

from hydrahive.llm import client as llm_client

logger = logging.getLogger(__name__)


async def call_with_tools(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[list[dict], str]:
    """One non-streaming LLM call with tool support.

    Returns (content_blocks, stop_reason). Stop-reason values from Anthropic:
    'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use' — the runner
    needs this to detect truncation (= broken tool_use inputs).
    """
    cfg = llm_client._load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if llm_client.is_minimax_model(target):
        minimax_key = llm_client._get_minimax_key(cfg)
        if not minimax_key:
            raise ValueError("MiniMax-API-Key fehlt — Provider 'minimax' in der LLM-Config setzen")
        return await _minimax_anthropic_call(
            api_key=minimax_key,
            model=llm_client._strip_provider_prefix(target),
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    anthropic_key = llm_client._get_anthropic_key(cfg)
    is_claude = llm_client._strip_provider_prefix(target).startswith("claude-")
    if not is_claude or not anthropic_key:
        raise NotImplementedError(
            "Nur Anthropic- und MiniMax-Pfad implementiert."
        )

    return await _anthropic_call(
        key=anthropic_key,
        model=llm_client._strip_provider_prefix(target),
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def _anthropic_call(
    *,
    key: str,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> list[dict]:
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
        system_blocks.append({"type": "text", "text": system_prompt})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_blocks:
        kwargs["system"] = system_blocks
    if tools:
        kwargs["tools"] = tools

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


async def _minimax_anthropic_call(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
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
    if system_prompt:
        kwargs["system"] = [{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]
    if tools:
        kwargs["tools"] = tools

    resp = await client.messages.create(**kwargs)
    blocks = [_block_to_dict(b) for b in resp.content]
    stop_reason = getattr(resp, "stop_reason", "") or ""
    return blocks, stop_reason


def _block_to_dict(block: Any) -> dict:
    """Anthropic SDK returns typed objects; normalize to plain dicts for DB-storage."""
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if hasattr(block, "dict"):
        return block.dict()
    if isinstance(block, dict):
        return block
    # Last-resort dump
    return json.loads(json.dumps(block, default=lambda o: getattr(o, "__dict__", str(o))))
