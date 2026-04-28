"""LLM-Call mit Streaming-Versuch + automatischem Fallback auf non-streaming.

Yields Events während Streaming. Letztes Yield ist ein `CallResult` (Sentinel)
mit den finalen Blocks und stop_reason. Caller iteriert events, prüft
isinstance(item, CallResult) für das Ende.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import AsyncIterator

from hydrahive.runner.events import Event, MessageStart, TextBlock, TextDelta
from hydrahive.runner.llm_bridge import call_with_tools
from hydrahive.runner.llm_bridge_stream import StreamingNotSupported, stream_with_tools

logger = logging.getLogger(__name__)


@dataclass
class CallResult:
    blocks: list[dict]
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


# Anthropic API-erlaubte Felder pro Block-Type. Das SDK fügt beim Streaming
# Convenience-Felder ein (parsed_output, caller, citations) die das API beim
# Re-Senden mit "Extra inputs are not permitted" ablehnt.
_ALLOWED_FIELDS = {
    "text": {"type", "text"},
    "tool_use": {"type", "id", "name", "input"},
    "thinking": {"type", "thinking", "signature"},
    "tool_result": {"type", "tool_use_id", "content", "is_error"},
}


def _sanitize_blocks(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for b in blocks:
        btype = b.get("type", "")
        allowed = _ALLOWED_FIELDS.get(btype)
        if allowed is None:
            out.append(b)
            continue
        out.append({k: v for k, v in b.items() if k in allowed})
    return out


async def call_with_stream_or_fallback(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[Event | CallResult]:
    """Tries streaming first; on any failure falls back to non-streaming.

    Last yield is always a CallResult.
    """
    streamed_ok = False
    blocks: list[dict] = []
    stop_reason = ""
    input_tokens = 0
    output_tokens = 0
    cache_creation = 0
    cache_read = 0

    try:
        async for raw_ev in stream_with_tools(
            model=model, system_prompt=system_prompt, messages=messages,
            tools=tools, temperature=temperature, max_tokens=max_tokens,
        ):
            t = raw_ev.get("type")
            if t == "message_start":
                yield MessageStart()
            elif t == "text_delta":
                yield TextDelta(text=raw_ev.get("text", ""))
            elif t == "message_stop":
                blocks = raw_ev.get("blocks", [])
                stop_reason = raw_ev.get("stop_reason", "")
                input_tokens = raw_ev.get("input_tokens", 0)
                output_tokens = raw_ev.get("output_tokens", 0)
                cache_creation = raw_ev.get("cache_creation_tokens", 0)
                cache_read = raw_ev.get("cache_read_tokens", 0)
                streamed_ok = True
                break
    except StreamingNotSupported as e:
        logger.info("Streaming nicht unterstützt: %s — Fallback", e)
    except Exception as e:
        logger.warning("Stream-Fehler — Fallback auf non-streaming: %s", e)

    if streamed_ok:
        yield CallResult(
            blocks=_sanitize_blocks(blocks), stop_reason=stop_reason,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cache_creation_tokens=cache_creation, cache_read_tokens=cache_read,
        )
        return

    # Fallback non-streaming
    fallback_blocks, fallback_stop = await call_with_tools(
        model=model, system_prompt=system_prompt, messages=messages,
        tools=tools, temperature=temperature, max_tokens=max_tokens,
    )
    text = "".join(b.get("text", "") for b in fallback_blocks if b.get("type") == "text")
    if text:
        yield TextBlock(text=text)
    yield CallResult(blocks=_sanitize_blocks(fallback_blocks), stop_reason=fallback_stop)
