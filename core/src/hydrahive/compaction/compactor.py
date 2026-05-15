from __future__ import annotations

import logging
import time

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
from hydrahive.db import compaction_events as compaction_events_db
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db

logger = logging.getLogger(__name__)

DEFAULT_RESERVE_TOKENS = 16_384
DEFAULT_KEEP_RECENT_TOKENS = 20_000
DEFAULT_MAX_TURNS_BEFORE_COMPACT = 24


def total_tokens(messages: list) -> int:
    return sum(estimate_message(m) for m in messages)


def should_compact(
    messages: list,
    model: str,
    *,
    reserve_tokens: int = DEFAULT_RESERVE_TOKENS,
    max_turns: int = DEFAULT_MAX_TURNS_BEFORE_COMPACT,
) -> bool:
    """Token-based OR turn-based — was zuerst hits."""
    if len(messages) >= max_turns:
        return True
    return total_tokens(messages) > (context_window_for(model) - reserve_tokens)


async def compact_session(
    session_id: str,
    *,
    model: str,
    keep_recent_tokens: int = DEFAULT_KEEP_RECENT_TOKENS,
    instructions: str | None = None,
    tool_result_limit: int | None = None,
    triggered_by: str = "auto",
    trigger_threshold_pct: int | None = None,
) -> dict:
    """Run one compaction pass. Returns metadata for logging/UI.

    `tool_result_limit` (#82): wenn gesetzt überschreibt es den serialize.py-
    Default. Bei riesen Sessions hilfreich (z.B. 500 statt 2000) damit der
    Dump ins Modell-Window passt.

    `triggered_by` + `trigger_threshold_pct`: Telemetrie-Felder fürs #129-Log,
    von den Callern (Runner=auto, API=manual) durchgereicht.
    """
    t0 = time.monotonic()
    session = sessions_db.get(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' nicht gefunden")

    # Telemetry-Snapshot — wird am Ende geschrieben (auch bei skipped/error).
    snap: dict = {
        "agent_id": session.agent_id,
        "user_id": session.user_id,
        "model": model,
        "triggered_by": triggered_by,
        "trigger_threshold_pct": trigger_threshold_pct,
        "instructions": instructions,
        "tool_result_limit": tool_result_limit,
        "skipped": False,
        "skip_reason": None,
        "skip_reason_params": None,
        "source": None,
        "messages_total": None,
        "messages_visible_before": None,
        "messages_to_summarize": None,
        "messages_kept": None,
        "tokens_before": None,
        "tokens_after_estimate": None,
        "cut_kept_from_index": None,
        "cut_is_split_turn": None,
        "cut_turn_prefix_count": None,
        "summary_chars": None,
        "summary_tokens_estimate": None,
        "facts_count": None,
        "files_extracted_count": None,
        "compaction_message_id": None,
        "had_previous_summary": None,
        "error": None,
    }

    def _emit() -> None:
        try:
            compaction_events_db.insert(compaction_events_db.CompactionEvent(
                session_id=session_id,
                duration_ms=int((time.monotonic() - t0) * 1000),
                **snap,
            ))
        except Exception:
            logger.exception("compaction_events-Insert fehlgeschlagen — Telemetrie verloren")

    try:
        full_history = messages_db.list_for_session(session_id)
        snap["messages_total"] = len(full_history)
        visible = resolve_through_compaction(full_history)
        snap["messages_visible_before"] = len(visible)
        snap["had_previous_summary"] = previous_summary_text(visible) is not None
        snap["tokens_before"] = total_tokens(visible)

        if len(visible) < 4:
            snap["skipped"] = True
            snap["skip_reason"] = "too_short"
            return {"skipped": True, "reason_code": "too_short"}

        cut = find_cut_point(visible, keep_recent_tokens)
        snap["cut_kept_from_index"] = cut.kept_from_index
        snap["cut_is_split_turn"] = cut.is_split_turn
        snap["cut_turn_prefix_count"] = cut.turn_prefix_count
        if cut.kept_from_index <= 0 and not cut.is_split_turn:
            snap["skipped"] = True
            snap["skip_reason"] = "nothing_to_compact"
            return {"skipped": True, "reason_code": "nothing_to_compact"}

        to_summarize = visible[: cut.kept_from_index]
        kept = visible[cut.kept_from_index:]
        snap["messages_to_summarize"] = len(to_summarize)
        snap["messages_kept"] = len(kept)
        if not to_summarize:
            snap["skipped"] = True
            snap["skip_reason"] = "empty_to_summarize"
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
                    snap["skipped"] = True
                    snap["skip_reason"] = "cancelled_by_hook"
                    snap["skip_reason_params"] = {"hook": h.name}
                    return {"skipped": True, "reason_code": "cancelled_by_hook", "reason_params": {"hook": h.name}}
                if res and res.summary:
                    snap["source"] = h.name
                    snap["summary_chars"] = len(res.summary)
                    snap["summary_tokens_estimate"] = len(res.summary) // 4
                    rec = persist_compaction(session_id, kept, res.summary, ctx, dict(res.details), source=h.name)
                    snap["compaction_message_id"] = rec.get("id")
                    snap["tokens_after_estimate"] = total_tokens(kept) + snap["summary_tokens_estimate"]
                    return rec

        # Hooks: pre-compact memory flush
        for h in all_hooks():
            if h.pre_compact_flush:
                try:
                    await h.pre_compact_flush(ctx)
                except Exception as e:
                    logger.warning("Pre-compact flush %s fehlgeschlagen: %s", h.name, e)

        # Hooks: structured facts
        facts = await collect_facts(ctx)
        snap["facts_count"] = len(facts) if facts is not None else 0

        # tool_result_limit-Param durchreichen — fallback auf serialize.py-Default
        serialize_kwargs = {}
        if tool_result_limit is not None:
            serialize_kwargs["tool_result_limit"] = tool_result_limit

        # Hooks: custom summarizer
        summary_text: str | None = None
        source = "default"
        for h in all_hooks():
            if h.custom_summarize:
                summary_text = await h.custom_summarize(ctx, serialize_for_summary(to_summarize, **serialize_kwargs))
                if summary_text:
                    source = h.name
                    break

        # Default summarizer
        if summary_text is None:
            history_text = serialize_for_summary(to_summarize, **serialize_kwargs)
            if instructions:
                history_text = f"BENUTZER-FOKUS: {instructions}\n\n{history_text}"
            summary_text = await summarize(
                model=model,
                serialized_history=history_text,
                previous_summary=ctx.previous_summary,
                facts=facts,
            )

        snap["source"] = source
        snap["summary_chars"] = len(summary_text)
        snap["summary_tokens_estimate"] = len(summary_text) // 4

        files = extract_files(to_summarize)
        snap["files_extracted_count"] = (
            len(files.get("readFiles", [])) + len(files.get("modifiedFiles", []))
        )
        details = {"facts": facts, **files}
        record = persist_compaction(session_id, kept, summary_text, ctx, details, source=source)
        snap["compaction_message_id"] = record.get("id")
        snap["tokens_after_estimate"] = total_tokens(kept) + snap["summary_tokens_estimate"]

        for h in all_hooks():
            if h.after_compact:
                try:
                    await h.after_compact(ctx, summary_text)
                except Exception as e:
                    logger.warning("After-compact hook %s fehlgeschlagen: %s", h.name, e)

        return record
    except Exception as e:
        snap["error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        _emit()
