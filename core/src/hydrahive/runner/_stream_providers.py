"""Provider-spezifische Stream-Implementierungen: Anthropic + MiniMax."""
from __future__ import annotations

from typing import Any, AsyncIterator

from hydrahive.llm import client as llm_client
from hydrahive.runner._anthropic_payload import (
    block_to_dict as _block_to_dict,
    build_anthropic_kwargs,
    build_minimax_kwargs,
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
    client, kwargs = build_anthropic_kwargs(
        key=key, model=model, system_prompt=system_prompt,
        volatile_system=volatile_system, summary_system=summary_system,
        cache_ttl=cache_ttl, messages=messages, tools=tools,
        temperature=temperature, max_tokens=max_tokens, reasoning_effort=reasoning_effort,
    )

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
    client, kwargs = build_minimax_kwargs(
        api_key=api_key, model=model, system_prompt=system_prompt,
        volatile_system=volatile_system, summary_system=summary_system,
        messages=messages, tools=tools, temperature=temperature,
        max_tokens=max_tokens, reasoning_effort=reasoning_effort,
    )

    async with client.messages.stream(**kwargs) as stream:
        async for ev in stream:
            mapped = _map_event(ev)
            if mapped is not None:
                yield mapped
        final = await stream.get_final_message()
        usage = getattr(final, "usage", None)
        yield {"type": "message_stop", "stop_reason": getattr(final, "stop_reason", "") or "",
               "blocks": [_block_to_dict(b) for b in (final.content or [])], **usage_dict(usage)}
