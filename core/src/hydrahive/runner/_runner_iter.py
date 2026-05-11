"""Runner — Pre-Iteration Helpers (Compaction-Trigger, System-Prompt-Bau, LLM-Call)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from hydrahive.compaction import compact_session, should_compact
from hydrahive.compaction.tokens import context_window_for
from hydrahive.db import messages as messages_db
from hydrahive.runner._call import CallResult, call_with_stream_or_fallback
from hydrahive.runner.events import Event

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    blocks: list[dict]
    stop_reason: str
    used_model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int


async def prepare_history(
    session_id: str,
    *,
    model: str,
    compact_model: str,
    compact_tool_limit: int | None,
    compact_reserve: int | None,
    compact_threshold_pct: int,
) -> list:
    """Holt aktuelle History und triggert Compaction wenn nötig."""
    history = messages_db.list_for_llm(session_id)
    effective_reserve = compact_reserve
    if effective_reserve is not None and compact_threshold_pct < 100:
        window = context_window_for(model)
        effective_reserve = max(
            effective_reserve,
            window - int(window * compact_threshold_pct / 100),
        )
    should_kwargs = {"reserve_tokens": effective_reserve} if effective_reserve is not None else {}
    if should_compact(history, model, **should_kwargs):
        try:
            compact_kwargs = {} if compact_tool_limit is None else {"tool_result_limit": compact_tool_limit}
            await compact_session(
                session_id, model=compact_model,
                triggered_by="auto", trigger_threshold_pct=compact_threshold_pct,
                **compact_kwargs,
            )
            history = messages_db.list_for_llm(session_id)
        except Exception as e:
            logger.warning("Compaction fehlgeschlagen: %s — fahre mit voller History fort", e)
    return history


def build_system_prompts(
    base_system_prompt: str,
    *,
    extra_system: str | None,
    workspace: Path,
    summary: str | None,
) -> tuple[str, str, str | None]:
    """Setzt stable-, volatile- und summary-System-Prompts zusammen.

    - stable: base + extra (cache-fähig über Sessions hinweg)
    - volatile: Datum/Uhrzeit + Workspace (ändert sich pro Call)
    - summary: bisherige Zusammenfassung als separater System-Block
    """
    stable_system = base_system_prompt
    if extra_system:
        stable_system = f"{extra_system}\n\n{stable_system}"

    now = datetime.now().astimezone()
    date_line = (
        f"Aktuelles Datum/Uhrzeit (Server): "
        f"{now.strftime('%Y-%m-%d %H:%M %Z')} ({now.strftime('%A')}). "
        f"Verwende dieses Datum als Referenz, NICHT dein Trainings-Cutoff."
    )
    workspace_line = f"Workspace: {workspace}"
    volatile_system = f"{date_line}\n\n{workspace_line}"
    summary_system = f"[Bisherige Zusammenfassung]\n{summary}" if summary else None

    return stable_system, volatile_system, summary_system


async def stream_llm_call(
    *,
    primary_model: str,
    fallback_models: list[str],
    stable_system: str,
    volatile_system: str,
    summary_system: str | None,
    cache_ttl: str,
    anth_messages: list[dict],
    tool_schemas: list[dict],
    temperature: float,
    max_tokens: int,
    reasoning_effort: str | None,
) -> AsyncIterator[Event | IterationResult]:
    """Macht den LLM-Call und streamt Events. Letzter yield ist genau ein
    `IterationResult`, alle anderen yields sind Events fürs Frontend.
    """
    models = [primary_model] + list(fallback_models or [])
    blocks: list[dict] = []
    stop_reason = ""
    used_model = primary_model
    input_tokens = output_tokens = cache_creation = cache_read = 0
    async for item in call_with_stream_or_fallback(
        models=models, system_prompt=stable_system, volatile_system=volatile_system,
        summary_system=summary_system, cache_ttl=cache_ttl,
        messages=anth_messages, tools=tool_schemas,
        temperature=temperature, max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    ):
        if isinstance(item, CallResult):
            blocks = item.blocks
            stop_reason = item.stop_reason
            input_tokens = item.input_tokens
            output_tokens = item.output_tokens
            cache_creation = item.cache_creation_tokens
            cache_read = item.cache_read_tokens
            used_model = item.model or primary_model
        else:
            yield item
    yield IterationResult(
        blocks=blocks, stop_reason=stop_reason, used_model=used_model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cache_creation_tokens=cache_creation, cache_read_tokens=cache_read,
    )
