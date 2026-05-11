"""llm_calls: Persistenz für LLM-API-Call-Telemetrie.

Eine Zeile pro Anthropic/OpenAI/etc.-Call mit Token-Usage, Timing, Cost.
Wird vom Runner nach jedem LLM-Aufruf befüllt — siehe `runner.py:run`.

Queries für Analyse laufen entweder direkt auf SQLite oder auf dem
PG-Mirror (siehe `_mirror_*.py`). Diese Datei liefert nur den Write-Path.
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass

from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlmCall:
    """Snapshot eines LLM-Calls für die DB."""
    session_id: str
    agent_id: str | None
    user_id: str | None
    provider: str
    model: str
    temperature: float | None
    max_tokens: int | None
    reasoning_effort: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cache_read_tokens: int | None
    cache_creation_tokens: int | None
    stop_reason: str | None
    ttft_ms: int | None
    total_ms: int | None
    cost_micros: int | None
    turn_in_session: int | None


def _new_id() -> str:
    return f"llmc_{secrets.token_hex(8)}"


def insert(call: LlmCall) -> str:
    """Schreibt einen LLM-Call. Returnt die generierte ID."""
    call_id = _new_id()
    with db() as conn:
        conn.execute(
            """INSERT INTO llm_calls (
                id, session_id, created_at,
                agent_id, user_id, provider, model,
                temperature, max_tokens, reasoning_effort,
                prompt_tokens, completion_tokens,
                cache_read_tokens, cache_creation_tokens,
                stop_reason, ttft_ms, total_ms, cost_micros,
                turn_in_session
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                call_id, call.session_id, now_iso(),
                call.agent_id, call.user_id, call.provider, call.model,
                call.temperature, call.max_tokens, call.reasoning_effort,
                call.prompt_tokens, call.completion_tokens,
                call.cache_read_tokens, call.cache_creation_tokens,
                call.stop_reason, call.ttft_ms, call.total_ms, call.cost_micros,
                call.turn_in_session,
            ),
        )
    return call_id


def for_session(session_id: str) -> list[dict]:
    """Holt alle LLM-Calls einer Session (Read-Path, primär für Tests + Debug)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM llm_calls WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
