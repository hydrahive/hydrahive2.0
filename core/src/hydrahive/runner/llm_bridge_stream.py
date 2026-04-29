"""Streaming-Variant des LLM-Calls.

Yields rohe Anthropic-Stream-Events. Caller (runner) macht das Mapping auf
unsere Event-Klassen + Block-Akkumulation. Tools-Support-Pfad nur Anthropic-OAuth
wie der non-streaming Bridge — LiteLLM/MiniMax kommt mit Provider-Ausbau.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from hydrahive.llm import client as llm_client

logger = logging.getLogger(__name__)


class StreamingNotSupported(RuntimeError):
    """Wird vom Caller gefangen → fallback auf non-streaming."""


async def stream_with_tools(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[dict]:
    """Yields normalized stream events as dicts.

    Event-Format:
      {"type": "message_start"}
      {"type": "block_start", "index": 0, "block_type": "text"}
      {"type": "block_start", "index": 1, "block_type": "tool_use", "id": "...", "name": "..."}
      {"type": "text_delta", "index": 0, "text": "..."}
      {"type": "input_delta", "index": 1, "json_partial": "..."}
      {"type": "block_stop", "index": 0}
      {"type": "message_stop", "stop_reason": "end_turn", "blocks": [...]}

    Bei Provider-Inkompatibilität: StreamingNotSupported geworfen — caller fallback.
    """
    cfg = llm_client._load_config()
    target = model or cfg.get("default_model", "")
    if not target:
        raise ValueError("Kein LLM-Modell konfiguriert")

    if llm_client.is_minimax_model(target):
        minimax_key = llm_client._get_minimax_key(cfg)
        if not minimax_key:
            raise StreamingNotSupported("MiniMax-API-Key fehlt")
        async for ev in _minimax_stream(
            api_key=minimax_key,
            model=llm_client._strip_provider_prefix(target),
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield ev
        return

    anthropic_key = llm_client._get_anthropic_key(cfg)
    is_claude = llm_client._strip_provider_prefix(target).startswith("claude-")
    if not (is_claude and anthropic_key.startswith("sk-ant-oat")):
        raise StreamingNotSupported("Streaming nur für Anthropic-OAuth + MiniMax implementiert")

    async for ev in _anthropic_oauth_stream(
        token=anthropic_key,
        model=llm_client._strip_provider_prefix(target),
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        yield ev


async def _anthropic_oauth_stream(
    *,
    token: str,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        api_key="",
        auth_token=token,
        timeout=300.0,
        default_headers=llm_client._ANTHROPIC_OAUTH_HEADERS,
    )

    # Identity + system_prompt mit cache_control — Anthropic-Prompt-Caching:
    # nach dem ersten Call werden diese Tokens als cache_read abgerechnet (10%).
    system_blocks = [
        {"type": "text", "text": llm_client._ANTHROPIC_OAUTH_IDENTITY[0]["text"]},
    ]
    if system_prompt:
        system_blocks.append({
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        })
    else:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    kwargs: dict[str, Any] = {
        "model": model,
        "system": system_blocks,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools

    async with client.messages.stream(**kwargs) as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        # Nach dem Stream: finale Message holen für stop_reason + Blocks + Usage
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {
            "type": "message_stop",
            "stop_reason": getattr(final, "stop_reason", "") or "",
            "blocks": [_block_to_dict(b) for b in (final.content or [])],
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
            "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0) if usage else 0,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
        }


async def _minimax_stream(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=llm_client.MINIMAX_BASE_URL,
        api_key=api_key,
        timeout=300.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )

    messages = llm_client.convert_images_for_minimax(messages)
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

    async with client.messages.stream(**kwargs) as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {
            "type": "message_stop",
            "stop_reason": getattr(final, "stop_reason", "") or "",
            "blocks": [_block_to_dict(b) for b in (final.content or [])],
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
            "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0) if usage else 0,
            "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
        }


def _map_event(ev: Any) -> dict | None:
    """Anthropic-SDK-Event → flat dict. None für Events die wir ignorieren."""
    et = getattr(ev, "type", "")
    if et == "message_start":
        return {"type": "message_start"}
    if et == "content_block_start":
        idx = getattr(ev, "index", 0)
        block = getattr(ev, "content_block", None)
        btype = getattr(block, "type", "") if block else ""
        out = {"type": "block_start", "index": idx, "block_type": btype}
        if btype == "tool_use":
            out["id"] = getattr(block, "id", "")
            out["name"] = getattr(block, "name", "")
        return out
    if et == "content_block_delta":
        idx = getattr(ev, "index", 0)
        delta = getattr(ev, "delta", None)
        dtype = getattr(delta, "type", "") if delta else ""
        if dtype == "text_delta":
            return {"type": "text_delta", "index": idx, "text": getattr(delta, "text", "")}
        if dtype == "input_json_delta":
            return {"type": "input_delta", "index": idx, "json_partial": getattr(delta, "partial_json", "")}
        return None
    if et == "content_block_stop":
        return {"type": "block_stop", "index": getattr(ev, "index", 0)}
    return None


def _block_to_dict(block: Any) -> dict:
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if isinstance(block, dict):
        return block
    return {"type": getattr(block, "type", "unknown")}
