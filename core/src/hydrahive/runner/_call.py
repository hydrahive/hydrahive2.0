"""LLM-Call mit Streaming-Versuch + Non-Streaming-Fallback + Modell-Failover.

Yields Events während Streaming. Letztes Yield ist ein `CallResult` (Sentinel)
mit den finalen Blocks und stop_reason. Caller iteriert events, prüft
isinstance(item, CallResult) für das Ende.

Failover-Strategie:
- Streaming wird nur auf dem primären Modell versucht (Mid-Stream-Fehler
  lassen sich nicht zurückrollen — User hätte schon Tokens gesehen).
- Bei Stream-Fehler ODER Streaming-not-supported wechselt der Pfad auf
  Non-Streaming und versucht alle Modelle der Reihe nach. Bei
  Quota/Overload-Fehlern (siehe `_failover.should_failover`) wird das
  nächste Modell probiert; nicht-failover-würdige Fehler werden raised.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import AsyncIterator

from hydrahive.runner._failover import should_failover
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
    # Welches Modell tatsächlich genutzt wurde — bei Failover ist primary !=
    # ausgeführtes. Frontend zeigt das im Bubble-Footer.
    model: str = ""


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
    models: list[str],
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[Event | CallResult]:
    """Tries streaming on primary; falls back to non-streaming with model failover."""
    if not models:
        raise ValueError("models darf nicht leer sein")

    primary = models[0]
    streamed_ok = False
    blocks: list[dict] = []
    stop_reason = ""
    input_tokens = output_tokens = cache_creation = cache_read = 0

    try:
        async for raw_ev in stream_with_tools(
            model=primary, system_prompt=system_prompt, messages=messages,
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
            model=primary,
        )
        return

    last_exc: Exception | None = None
    for i, model in enumerate(models):
        is_last = i == len(models) - 1
        try:
            fallback_blocks, fallback_stop = await call_with_tools(
                model=model, system_prompt=system_prompt, messages=messages,
                tools=tools, temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            if should_failover(e) and not is_last:
                next_model = models[i + 1]
                logger.warning("LLM-Failover %s → %s wegen: %s", model, next_model, e)
                last_exc = e
                continue
            raise
        text = "".join(b.get("text", "") for b in fallback_blocks if b.get("type") == "text")
        if text:
            yield TextBlock(text=text)
        yield CallResult(
            blocks=_sanitize_blocks(fallback_blocks), stop_reason=fallback_stop,
            model=model,
        )
        return

    raise last_exc or RuntimeError("Alle Modelle fehlgeschlagen")
