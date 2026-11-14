"""Nicht-Streaming-Teil der Modellkette (Rückfall aus `_call.py`).

Läuft ab dem Modell, bei dem das Streaming aufgegeben hat. Verbindungsaussetzer werden je Modell bis zu
STALL_ATTEMPTS-mal auf frischer Verbindung wiederholt (Messung hydratest 5.11., 150 Läufe). Danach – oder bei
Anbieterfehlern – kommt das nächste Modell dran. Leere Antworten wechseln ebenfalls (außer beim letzten Modell).
Liefert Events (`ModelSwitch`) und am Ende genau ein Tupel (modell, blocks, stop_reason, usage).

Die Aufruf-Funktion wird übergeben (nicht importiert), damit Tests sie an `_call` austauschen können.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable

from hydrahive.runner import _model_cooldown as cooldown
from hydrahive.runner._call_stream import _CONNECTION_ERRORS, _STALL_PAUSE, STALL_ATTEMPTS
from hydrahive.runner._call_tools import tools_for
from hydrahive.runner._failover import PROVIDER_CATEGORIES, SWITCH_CATEGORIES, classify
from hydrahive.runner.context import has_visible_content

logger = logging.getLogger("hydrahive.runner._call")


async def _with_connection_retry(call_fn: Callable[..., Any], **kwargs):
    for attempt in range(STALL_ATTEMPTS):
        try:
            return await call_fn(**kwargs)
        except _CONNECTION_ERRORS as e:
            if attempt == STALL_ATTEMPTS - 1:
                raise
            logger.warning("Fallback-Aufruf (Versuch %d) — retry in %gs: %s: %s",
                           attempt + 1, _STALL_PAUSE, type(e).__name__, e)
            from hydrahive.runner import _call
            await _call.asyncio.sleep(_STALL_PAUSE)


async def call_chain_non_streaming(
    call_fn: Callable[..., Any],
    models: list[str],
    base: dict[str, Any],
    tools: list[dict],
    switch_log: list[dict],
    *,
    cooldown_seconds: int,
    make_switch: Callable[[list[dict], str, str, str], Any],
) -> AsyncIterator[Any]:
    for i, model in enumerate(models):
        has_next = i < len(models) - 1
        try:
            blocks, stop, usage = await _with_connection_retry(call_fn, **base, model=model,
                                                               tools=tools_for(model, tools))
        except Exception as e:
            reason = classify(e)
            if has_next and reason in SWITCH_CATEGORIES:
                if reason in PROVIDER_CATEGORIES:
                    cooldown.mark_down(model, cooldown_seconds)
                yield make_switch(switch_log, model, models[i + 1], reason)
                continue
            raise
        if not has_visible_content(blocks) and has_next:
            yield make_switch(switch_log, model, models[i + 1], "empty")
            continue
        yield (model, blocks, stop, usage)
        return
    raise RuntimeError("Alle Modelle fehlgeschlagen")
