"""Provider-spezifische Stream-Implementierungen: Anthropic + MiniMax."""
from __future__ import annotations

from typing import Any, AsyncIterator

from hydrahive.llm import client as llm_client


def _map_event(ev: Any) -> dict | None:
    et = getattr(ev, "type", "")
    if et == "message_start":
        return {"type": "message_start"}
    if et == "content_block_start":
        idx = getattr(ev, "index", 0)
        block = getattr(ev, "content_block", None)
        btype = getattr(block, "type", "") if block else ""
        out: dict[str, Any] = {"type": "block_start", "index": idx, "block_type": btype}
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


def _cache_control(ttl: str) -> dict:
    ctrl: dict[str, Any] = {"type": "ephemeral"}
    if ttl and ttl != "5m":
        ctrl["ttl"] = ttl
    return ctrl


def _block_to_dict(block: Any) -> dict:
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if isinstance(block, dict):
        return block
    return {"type": getattr(block, "type", "unknown")}


def _usage_dict(usage: Any) -> dict:
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        "cache_creation_tokens": getattr(usage, "cache_creation_input_tokens", 0) if usage else 0,
        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
    }


async def anthropic_stream(
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
    reasoning_effort: str | None = None,
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    from hydrahive.llm._anthropic import apply_thinking_budget
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

    kwargs: dict[str, Any] = {"model": model, "messages": messages,
                              "temperature": temperature, "max_tokens": max_tokens}
    if system_blocks:
        kwargs["system"] = system_blocks
    if tools:
        kwargs["tools"] = tools
    apply_thinking_budget(kwargs, reasoning_effort)

    try:
        cm = client.messages.stream(**kwargs)
    except _anthropic.BadRequestError as e:
        if "temperature" in str(e).lower() and "deprecated" in str(e).lower():
            kwargs.pop("temperature", None)
            cm = client.messages.stream(**kwargs)
        else:
            raise

    async with cm as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {"type": "message_stop", "stop_reason": getattr(final, "stop_reason", "") or "",
               "blocks": [_block_to_dict(b) for b in (final.content or [])], **_usage_dict(usage)}


async def minimax_stream(
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
    reasoning_effort: str | None = None,  # noqa: ARG001 (kein Reasoning-Support)
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(
        base_url=llm_client.MINIMAX_BASE_URL, api_key=api_key, timeout=300.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )

    kwargs: dict[str, Any] = {"model": model, "messages": messages,
                              "temperature": temperature, "max_tokens": max_tokens}
    if system_prompt or volatile_system:
        blocks: list[dict[str, Any]] = []
        if system_prompt:
            blocks.append({"type": "text", "text": system_prompt, "cache_control": _cache_control(cache_ttl)})
        if volatile_system:
            blocks.append({"type": "text", "text": volatile_system})
        kwargs["system"] = blocks
    if tools:
        kwargs["tools"] = tools

    async with client.messages.stream(**kwargs) as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {"type": "message_stop", "stop_reason": getattr(final, "stop_reason", "") or "",
               "blocks": [_block_to_dict(b) for b in (final.content or [])], **_usage_dict(usage)}
