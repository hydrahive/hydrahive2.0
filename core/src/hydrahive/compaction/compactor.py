from __future__ import annotations

import logging

from hydrahive.compaction._storage import (
    extract_files,
    persist_compaction,
    previous_summary_text,
    resolve_through_compaction,
)
from hydrahive.compaction.cut_point import find_cut_point
from hydrahive.compaction.hooks import CompactionContext, all_hooks, collect_facts
from hydrahive.compaction.serialize import serialize_for_summary
from hydrahive.compaction.summarize import summarize
from hydrahive.compaction.tokens import context_window_for, estimate_message
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db

logger = logging.getLogger(__name__)

DEFAULT_RESERVE_TOKENS = 16_384
DEFAULT_KEEP_RECENT_TOKENS = 20_000


def total_tokens(messages: list) -> int:
    return sum(estimate_message(m) for m in messages)


def should_compact(
    messages: list,
    model: str,
    *,
    reserve_tokens: int = DEFAULT_RESERVE_TOKENS,
) -> bool:
    """OpenClaw rule: contextTokens > contextWindow - reserveTokens."""
    return total_tokens(messages) > (context_window_for(model) - reserve_tokens)


async def compact_session(
    session_id: str,
    *,
    model: str,
    keep_recent_tokens: int = DEFAULT_KEEP_RECENT_TOKENS,
    instructions: str | None = None,
) -> dict:
    """Run one compaction pass. Returns metadata for logging/UI."""
    session = sessions_db.get(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' nicht gefunden")

    full_history = messages_db.list_for_session(session_id)
    visible = resolve_through_compaction(full_history)
    if len(visible) < 4:
        return {"skipped": True, "reason_code": "too_short"}

    cut = find_cut_point(visible, keep_recent_tokens)
    if cut.kept_from_index <= 0 and not cut.is_split_turn:
        return {"skipped": True, "reason_code": "nothing_to_compact"}

    to_summarize = visible[: cut.kept_from_index]
    kept = visible[cut.kept_from_index:]
    if not to_summarize:
        return {"skipped": True, "reason_code": "empty_to_summarize"}

    ctx = CompactionContext(
        session_id=session_id,
        agent_id=session.agent_id,
        user_id=session.user_id,
        messages_before_cut=to_summarize,
        messages_after_cut=kept,
        is_split_turn=cut.is_split_turn,
        turn_prefix_count=cut.turn_prefix_count,
        previous_summary=previous_summary_text(visible),
        tokens_before=total_tokens(visible),
    )

    # Hooks: cancel or custom-summary
    for h in all_hooks():
        if h.before_compact:
            res = await h.before_compact(ctx)
            if res and res.cancel:
                return {"skipped": True, "reason_code": "cancelled_by_hook", "reason_params": {"hook": h.name}}
            if res and res.summary:
                return persist_compaction(session_id, kept, res.summary, ctx, dict(res.details), source=h.name)

    # Hooks: pre-compact memory flush
    for h in all_hooks():
        if h.pre_compact_flush:
            try:
                await h.pre_compact_flush(ctx)
            except Exception as e:
                logger.warning("Pre-compact flush %s fehlgeschlagen: %s", h.name, e)

    # Hooks: structured facts
    facts = await collect_facts(ctx)

    # Hooks: custom summarizer
    summary_text: str | None = None
    for h in all_hooks():
        if h.custom_summarize:
            summary_text = await h.custom_summarize(ctx, serialize_for_summary(to_summarize))
            if summary_text:
                break

    # Default summarizer
    if summary_text is None:
        history_text = serialize_for_summary(to_summarize)
        if instructions:
            history_text = f"BENUTZER-FOKUS: {instructions}\n\n{history_text}"
        summary_text = await summarize(
            model=model,
            serialized_history=history_text,
            previous_summary=ctx.previous_summary,
            facts=facts,
        )

    details = {"facts": facts, **extract_files(to_summarize)}
    record = persist_compaction(session_id, kept, summary_text, ctx, details, source="default")

    for h in all_hooks():
        if h.after_compact:
            try:
                await h.after_compact(ctx, summary_text)
            except Exception as e:
                logger.warning("After-compact hook %s fehlgeschlagen: %s", h.name, e)

    return record
