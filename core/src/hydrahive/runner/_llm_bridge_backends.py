"""Anthropic + MiniMax backend calls for llm_bridge."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.llm import client as llm_client


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


async def minimax_anthropic_call(
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
