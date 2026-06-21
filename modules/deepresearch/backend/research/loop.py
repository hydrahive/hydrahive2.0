"""Iterativer Research-Controller (IterResearch-Stil).

plan → pro Runde [queries → gather → synthesize → stop?] → finaler Bericht.
Bewusst lokal-modell-tauglich: großzügige Runden/Timeouts, alles best-effort.
"""
from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from . import planner, queries, synthesize
from .gather import gather_round
from .models import RunState
from .report_writer import write_report

logger = logging.getLogger(__name__)

ProgressCb = Callable[[dict], Awaitable[None]] | Callable[[dict], None] | None


async def _emit(cb: ProgressCb, state: RunState, phase: str) -> None:
    if cb is None:
        return
    payload = {
        "phase": phase,
        "round": state.round,
        "queries": len(state.queries_used),
        "urls": len(state.urls_seen),
        "findings": len(state.findings),
        "category": state.category,
    }
    res = cb(payload)
    if res is not None and hasattr(res, "__await__"):
        await res


async def run_research(
    state: RunState,
    *,
    progress: ProgressCb = None,
    max_rounds: int = 6,
    min_rounds: int = 2,
    max_time: float = 300.0,
) -> dict:
    """Führt den Lauf aus und gibt {markdown, sources, stats, category} zurück."""
    started = time.monotonic()

    await planner.make_plan(state)
    await _emit(progress, state, "planned")

    for rnd in range(1, max_rounds + 1):
        state.round = rnd
        first = rnd == 1
        qs = await queries.generate_queries(state, first)
        await _emit(progress, state, "searching")
        if qs:
            await gather_round(state, qs)
        await _emit(progress, state, "synthesizing")
        await synthesize.synthesize(state)

        if rnd >= min_rounds and time.monotonic() - started < max_time:
            if await synthesize.should_stop(state):
                break
        if time.monotonic() - started >= max_time:
            logger.info("deepresearch: Zeitbudget erreicht nach Runde %s", rnd)
            break

    await _emit(progress, state, "writing")
    markdown = await write_report(state)

    stats = {
        "rounds": state.round,
        "queries": len(state.queries_used),
        "urls": len(state.urls_seen),
        "sources": len(state.sources()),
        "duration_s": round(time.monotonic() - started, 1),
        "model": state.model or "default",
    }
    return {
        "markdown": markdown,
        "sources": state.sources(),
        "stats": stats,
        "category": state.category,
    }
