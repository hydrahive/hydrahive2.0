"""Runner — Pre-Iteration Helpers (Compaction-Trigger, LLM-Call)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

from hydrahive.compaction import (
    compact_session,
    compact_threshold_tokens,
    effective_reserve_tokens,
    should_compact,
)
from hydrahive.db import compaction_events as compaction_events_db
from hydrahive.db import messages as messages_db
from hydrahive.runner._call import CallResult, call_with_stream_or_fallback
from hydrahive.runner._measured_usage import measured_history_tokens
from hydrahive.runner.events import CompactionStart, Event

logger = logging.getLogger(__name__)

AUTO_COMPACTION_COOLDOWN_SECONDS = 300


def _measured_over_threshold(
    session_id: str, history: list, model: str, *, threshold_pct: int, reserve_tokens: int | None,
) -> bool:
    """Zweiter Trigger: echte Prompt-Größe laut Provider statt nur Zeichen-Schätzung (siehe _measured_usage)."""
    if not history:
        return False
    measured = measured_history_tokens(
        history, model=model, compacted_at=messages_db.latest_compaction_at(session_id),
    )
    if measured <= 0:
        return False
    threshold = compact_threshold_tokens(model, threshold_pct=threshold_pct, reserve_tokens=reserve_tokens)
    if measured <= threshold:
        return False
    logger.info(
        "Compaction-Trigger (gemessen) für Session %s: %d Tokens > Schwelle %d (%s)",
        session_id, measured, threshold, model,
    )
    return True


def _auto_compaction_cooldown_active(
    session_id: str,
    *,
    now: datetime | None = None,
) -> bool:
    latest = compaction_events_db.latest_for_session(session_id)
    error = str(latest.get("error") or "") if latest else ""
    if (
        not error
        or latest.get("triggered_by") != "auto"
        or error.startswith("CancelledError")
    ):
        return False
    try:
        created = datetime.fromisoformat(str(latest["created_at"]).replace("Z", "+00:00"))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        logger.warning("Compaction-Cooldown: ungültiger Zeitstempel für Session %s", session_id)
        return False
    current = now or datetime.now(timezone.utc)
    age = (current.astimezone(timezone.utc) - created.astimezone(timezone.utc)).total_seconds()
    return 0 <= age < AUTO_COMPACTION_COOLDOWN_SECONDS


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
    compact_fallback_models: list[str],
    compact_tool_limit: int | None,
    compact_reserve: int | None,
    compact_threshold_pct: int,
    compact_max_turns: int | None,
):
    """Holt aktuelle History und triggert Compaction wenn nötig.

    AsyncGenerator: yieldet zuerst optionale Events (CompactionStart),
    letzter yield ist immer die History-Liste.
    """
    history = messages_db.list_for_llm(session_id)
    effective_reserve = effective_reserve_tokens(
        model, threshold_pct=compact_threshold_pct, reserve_tokens=compact_reserve
    )
    should_kwargs: dict = {}
    if effective_reserve is not None:
        should_kwargs["reserve_tokens"] = effective_reserve
    if compact_max_turns is not None:
        should_kwargs["max_turns"] = compact_max_turns
    if should_compact(history, model, **should_kwargs) or _measured_over_threshold(
        session_id, history, model,
        threshold_pct=compact_threshold_pct, reserve_tokens=compact_reserve,
    ):
        if _auto_compaction_cooldown_active(session_id):
            logger.warning(
                "Auto-Compaction für Session %s im %ss-Cooldown — fahre mit voller History fort",
                session_id,
                AUTO_COMPACTION_COOLDOWN_SECONDS,
            )
        else:
            yield CompactionStart()
            try:
                compact_kwargs = {} if compact_tool_limit is None else {"tool_result_limit": compact_tool_limit}
                await compact_session(
                    session_id, model=compact_model, fallback_models=compact_fallback_models,
                    triggered_by="auto", trigger_threshold_pct=compact_threshold_pct,
                    **compact_kwargs,
                )
                history = messages_db.list_for_llm(session_id)
            except Exception as e:
                logger.warning("Compaction fehlgeschlagen: %s — fahre mit voller History fort", e)
    yield history



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
