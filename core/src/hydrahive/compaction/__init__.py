"""Compaction-Layer für HydraHive2.

OpenClaw-Architektur (append-only mit firstKeptEntryId-Pointer) plus
HydraHive-Borrows (Secret-Redaction, Cumulative File-Tracking, Plugin-Hooks).

Public API:
    should_compact(messages, model)        — Schwellen-Check
    compact_session(session_id, ...)       — eine Compaction-Pass durchführen
    list_for_llm(session_id)               — History resolved für LLM-Call
    hooks                                   — Plugin-Hook-System
"""

from hydrahive.compaction.compactor import (
    DEFAULT_KEEP_RECENT_TOKENS,
    DEFAULT_RESERVE_TOKENS,
    compact_session,
    should_compact,
    total_tokens,
)
from hydrahive.compaction.hooks import (
    CompactionContext,
    CompactionHooks,
    CompactionResult,
    register,
)

__all__ = [
    "should_compact",
    "compact_session",
    "total_tokens",
    "DEFAULT_RESERVE_TOKENS",
    "DEFAULT_KEEP_RECENT_TOKENS",
    "CompactionContext",
    "CompactionHooks",
    "CompactionResult",
    "register",
]
