"""compaction_events: Persistenz für Compaction-Telemetrie.

Eine Zeile pro `compact_session()`-Aufruf — auch für skipped + crashed.
Wird vom Compactor nach jedem Pass befüllt (siehe `compactor.py`).

Queries laufen entweder direkt auf SQLite oder auf dem PG-Mirror.
Diese Datei liefert nur den Write-Path.
"""
from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompactionEvent:
    """Snapshot eines Compaction-Passes für die DB."""
    session_id: str
    agent_id: str | None
    user_id: str | None
    triggered_by: str | None
    trigger_threshold_pct: int | None
    model: str | None
    source: str | None
    instructions: str | None
    tool_result_limit: int | None
    skipped: bool
    skip_reason: str | None
    skip_reason_params: dict | None
    messages_total: int | None
    messages_visible_before: int | None
    messages_to_summarize: int | None
    messages_kept: int | None
    tokens_before: int | None
    tokens_after_estimate: int | None
    cut_kept_from_index: int | None
    cut_is_split_turn: bool | None
    cut_turn_prefix_count: int | None
    summary_chars: int | None
    summary_tokens_estimate: int | None
    facts_count: int | None
    files_extracted_count: int | None
    compaction_message_id: str | None
    had_previous_summary: bool | None
    duration_ms: int | None
    error: str | None


def _new_id() -> str:
    return f"cmpe_{secrets.token_hex(8)}"


def insert(event: CompactionEvent) -> str:
    """Schreibt ein Compaction-Event. Returnt die generierte ID."""
    event_id = _new_id()
    with db() as conn:
        conn.execute(
            """INSERT INTO compaction_events (
                id, session_id, created_at,
                agent_id, user_id,
                triggered_by, trigger_threshold_pct, model, source,
                instructions, tool_result_limit,
                skipped, skip_reason, skip_reason_params,
                messages_total, messages_visible_before,
                messages_to_summarize, messages_kept,
                tokens_before, tokens_after_estimate,
                cut_kept_from_index, cut_is_split_turn, cut_turn_prefix_count,
                summary_chars, summary_tokens_estimate,
                facts_count, files_extracted_count,
                compaction_message_id, had_previous_summary,
                duration_ms, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id, event.session_id, now_iso(),
                event.agent_id, event.user_id,
                event.triggered_by, event.trigger_threshold_pct, event.model, event.source,
                event.instructions, event.tool_result_limit,
                1 if event.skipped else 0,
                event.skip_reason,
                json.dumps(event.skip_reason_params) if event.skip_reason_params else None,
                event.messages_total, event.messages_visible_before,
                event.messages_to_summarize, event.messages_kept,
                event.tokens_before, event.tokens_after_estimate,
                event.cut_kept_from_index,
                None if event.cut_is_split_turn is None else (1 if event.cut_is_split_turn else 0),
                event.cut_turn_prefix_count,
                event.summary_chars, event.summary_tokens_estimate,
                event.facts_count, event.files_extracted_count,
                event.compaction_message_id,
                None if event.had_previous_summary is None else (1 if event.had_previous_summary else 0),
                event.duration_ms, event.error,
            ),
        )
    return event_id


def for_session(session_id: str) -> list[dict]:
    """Holt alle Compaction-Events einer Session (Read-Path)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM compaction_events WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
