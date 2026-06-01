"""Provider-spezifische Stream-Implementierungen: Anthropic + MiniMax."""
from __future__ import annotations

from typing import Any, AsyncIterator

from hydrahive.llm import client as llm_client
from hydrahive.runner._anthropic_payload import (
    add_cache_reference_to_tool_results as _add_cache_reference_to_tool_results,
    block_to_dict as _block_to_dict,
    cache_control as _cache_control,
    with_cache_breakpoint as _with_cache_breakpoint,
)
from hydrahive.runner._token_usage import usage_dict


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
        # thinking_delta und andere unbekannte Delta-Typen werden verworfen
        return None
    if et == "content_block_stop":
        return {"type": "block_stop", "index": getattr(ev, "index", 0)}
    return None


def _strip_minimax_cache_control(messages: list[dict], tools: list[dict]) -> tuple[list[dict], list[dict]]:
    """Entfernt cache_control aus Messages und Tools — MiniMax wirft sonst HTTP 500."""
    clean: list[dict] = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            stripped = [{k: v for k, v in b.items() if k != "cache_control"} for b in content]
            clean.append({**msg, "content": stripped})
        else:
            clean.append(msg)
    clean_tools = [{k: v for k, v in t.items() if k != "cache_control"} for t in tools]
    return clean, clean_tools


async def anthropic_stream(
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
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    from hydrahive.llm._anthropic import apply_effort
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
    if summary_system:
        system_blocks.append({"type": "text", "text": summary_system, "cache_control": _cache_control(cache_ttl)})
    if volatile_system:
        system_blocks.append({"type": "text", "text": volatile_system})

    kwargs: dict[str, Any] = {"model": model, "messages": _with_cache_breakpoint(messages, ttl=cache_ttl),
                              "temperature": temperature, "max_tokens": max_tokens}
    if system_blocks:
        kwargs["system"] = system_blocks
    if tools:
        cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
        kwargs["tools"] = cached_tools
    apply_effort(kwargs, model, reasoning_effort)

    async def _consume(kw: dict[str, Any]) -> AsyncIterator[dict]:
        # Das async with löst den eigentlichen HTTP-Request in __aenter__ aus —
        # muss daher INNERHALB des try/except liegen, sonst greift der Retry nicht.
        async with client.messages.stream(**kw) as stream:
            async for ev in stream:
                mapped = _map_event(ev)
                if mapped is not None:
                    yield mapped
            final = await stream.get_final_message()
            usage = getattr(final, "usage", None)
            yield {"type": "message_stop", "stop_reason": getattr(final, "stop_reason", "") or "",
                   "blocks": [_block_to_dict(b) for b in (final.content or [])], **usage_dict(usage)}

    yielded = False
    try:
        async for ev in _consume(kwargs):
            yielded = True
            yield ev
    except _anthropic.BadRequestError as e:
        # temperature ist bei manchen neueren Claude-Modellen (opus 4.7/4.8) deprecated.
        # Der Fehler feuert beim Request-Start (__aenter__) vor dem ersten Event —
        # nur dann ist ein Retry ohne temperature sicher (kein doppeltes Streaming).
        if not yielded and "temperature" in str(e).lower() and "deprecated" in str(e).lower():
            kwargs.pop("temperature", None)
            async for ev in _consume(kwargs):
                yield ev
        else:
            raise


async def minimax_stream(
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
) -> AsyncIterator[dict]:
    import anthropic as _anthropic
    from hydrahive.llm._anthropic import apply_effort
    client = _anthropic.AsyncAnthropic(
        base_url=llm_client.MINIMAX_BASE_URL, api_key=api_key, timeout=300.0,
        default_headers={"Authorization": f"Bearer {api_key}"},
    )

    messages, tools = _strip_minimax_cache_control(messages, tools)
    kwargs: dict[str, Any] = {"model": model, "messages": messages,
                              "temperature": temperature, "max_tokens": max_tokens}
    if system_prompt or summary_system or volatile_system:
        # MiniMax: system als einzelner String — Array mit mehreren Blöcken
        # führt nach Compaction (3 Blöcke) zu HTTP 500 "input json is empty".
        parts = [p for p in [system_prompt, summary_system, volatile_system] if p]
        kwargs["system"] = "\n\n".join(parts)
    if tools:
        kwargs["tools"] = tools

    apply_effort(kwargs, model, reasoning_effort)

    async with client.messages.stream(**kwargs) as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {"type": "message_stop", "stop_reason": getattr(final, "stop_reason", "") or "",
               "blocks": [_block_to_dict(b) for b in (final.content or [])], **usage_dict(usage)}
