"""LLM-Call mit Modellkette: Streaming je Modell, Nicht-Streaming als Rückfall, Wechsel bei Ausfällen.

Yields Events während Streaming. Letztes Yield ist ein `CallResult` (Sentinel) mit den finalen Blocks und
stop_reason. Caller iteriert events, prüft isinstance(item, CallResult) für das Ende.

Kette (Spec agent-templates.md Kap. 8):
1. Gesperrte Modelle (kurz zuvor Anbieterfehler) werden übersprungen, außer alle sind gesperrt.
2. Jedes Modell wird gestreamt (Wiederholregeln in `_call_stream.py`).
   - Anbieterfehler vor dem ersten Text → Modell sperren, nächstes Modell streamen.
   - Timeout/Verbindungsabbruch nach allen Wiederholversuchen → nächstes Modell streamen.
   - Leere Antwort (kein Text, kein Werkzeug) → dasselbe Modell einmal erneut, dann nächstes (beim letzten
     Modell bleibt die leere Antwort stehen, der Runner meldet sie).
   - Streaming nicht unterstützt, Text schon gesendet oder sonstiger Fehler → Nicht-Streaming (Schritt 3).
3. Nicht-Streaming ab dem aktuellen Modell, mit Wechsel bei denselben Gründen.
Jeder Wechsel wird als `ModelSwitch` gemeldet und steht in `CallResult.switches`.
"""
from __future__ import annotations

import asyncio  # noqa: F401 — Tests patchen _call.asyncio.sleep (Unter-Module schlafen darüber)
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from hydrahive.runner import _model_cooldown as cooldown
from hydrahive.runner._call_fallback import call_chain_non_streaming
from hydrahive.runner._codex_provider import CodexModelNotAllowed, CodexStreamStall  # noqa: F401 — Re-Export
from hydrahive.runner._call_stream import (  # noqa: F401 — Re-Export (Tests, Aufrufer)
    _CONNECTION_ERRORS,
    _STALL_PAUSE,
    STALL_ATTEMPTS,
    StreamOutcome,
    stream_attempts,
)
from hydrahive.runner._call_tools import sanitize_blocks, tools_for
from hydrahive.runner._failover import PROVIDER_CATEGORIES, SWITCH_CATEGORIES
from hydrahive.runner.context import has_visible_content
from hydrahive.runner.events import Event, ModelSwitch
from hydrahive.runner.llm_bridge import call_with_tools
from hydrahive.runner.llm_bridge_stream import StreamingNotSupported, stream_with_tools  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass
class CallResult:
    blocks: list[dict]
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    # Welches Modell tatsächlich genutzt wurde — bei Failover ist primary != ausgeführtes.
    model: str = ""
    # Modellwechsel in diesem Aufruf: [{"from_model", "to_model", "reason"}]
    switches: list[dict] = field(default_factory=list)


def _switch(log: list[dict], src: str, dst: str, reason: str) -> ModelSwitch:
    logger.warning("LLM-Failover %s → %s wegen: %s", src, dst, reason)
    log.append({"from_model": src, "to_model": dst, "reason": reason})
    return ModelSwitch(from_model=src, to_model=dst, reason=reason)


async def call_with_stream_or_fallback(
    *,
    models: list[str],
    system_prompt: str,
    volatile_system: str | None = None,
    summary_system: str | None = None,
    cache_ttl: str = "1h",
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None = None,
    cooldown_seconds: int = cooldown.DEFAULT_COOLDOWN_SECONDS,
) -> AsyncIterator[Event | CallResult]:
    """Modellkette: Streaming je Modell, Nicht-Streaming als Rückfall, Wechsel bei Ausfällen."""
    if not models:
        raise ValueError("models darf nicht leer sein")

    switch_log: list[dict] = []
    chain, skipped = cooldown.available(models)
    if skipped and models[0] in skipped:
        yield _switch(switch_log, models[0], chain[0], "cooldown")
    base = dict(system_prompt=system_prompt, volatile_system=volatile_system, summary_system=summary_system,
                cache_ttl=cache_ttl, messages=messages, temperature=temperature, max_tokens=max_tokens,
                reasoning_effort=reasoning_effort)

    i = 0
    empty_retry_done = False
    while i < len(chain):
        model = chain[i]
        has_next = i < len(chain) - 1
        out = StreamOutcome()
        kwargs = dict(base, model=model, tools=tools_for(model, tools))
        async for ev in stream_attempts(stream_with_tools, kwargs, out, has_next=has_next):
            yield ev

        if out.ok:
            visible = has_visible_content(out.blocks) or out.text_sent
            if visible or (not has_next and empty_retry_done):
                yield CallResult(blocks=sanitize_blocks(out.blocks), stop_reason=out.stop_reason, model=model,
                                 switches=switch_log, **out.usage)
                return
            if not empty_retry_done:   # auch beim letzten Modell (Task e813b45f)
                logger.warning("Leere Antwort von %s — ein weiterer Versuch auf demselben Modell", model)
                empty_retry_done = True
                continue
            yield _switch(switch_log, model, chain[i + 1], "empty")
            i += 1
            empty_retry_done = False
            continue

        if has_next and not out.text_sent and out.reason in SWITCH_CATEGORIES:
            if out.reason in PROVIDER_CATEGORIES:
                cooldown.mark_down(model, cooldown_seconds)
            yield _switch(switch_log, model, chain[i + 1], out.reason)
            i += 1
            empty_retry_done = False
            continue
        break   # Streaming nicht unterstützt / Text gesendet / sonstiger Fehler → Nicht-Streaming ab hier

    async for item in call_chain_non_streaming(
        call_with_tools, chain[i:], base, tools, switch_log, cooldown_seconds=cooldown_seconds,
        make_switch=_switch,
    ):
        if isinstance(item, tuple):
            model, blocks, stop, usage = item
            yield CallResult(
                blocks=sanitize_blocks(blocks), stop_reason=stop,
                input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                cache_creation_tokens=usage.get("cache_creation_tokens", 0),
                cache_read_tokens=usage.get("cache_read_tokens", 0),
                model=model, switches=switch_log,
            )
            return
        yield item
