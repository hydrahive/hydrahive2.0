"""Plugin-Hook-Interface für Compaction.

Plugins registrieren Hooks via `register()`. Default-Verhalten ohne Plugins:
OpenClaw-Stil mit eingebauter Secret-Redaction.

Sechs Extension-Points:
  - before_compact     : Plugin kann cancel zurückgeben oder eigene Summary liefern
  - extract_facts      : strukturierte Fakten extrahieren (TaskStateFacts-artig)
  - pre_compact_flush  : wichtigen Kontext woanders sichern bevor verdichtet wird
  - custom_summarize   : eigenen Summarizer einklinken (z.B. anderes Modell)
  - after_compact      : Logging, Metrics, Side-Effects
  - redact_pattern     : zusätzliche Secret-Patterns hinzufügen
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass
class CompactionContext:
    """Wird allen Hooks übergeben."""
    session_id: str
    agent_id: str
    user_id: str
    messages_before_cut: list  # die zu kompaktierenden Messages
    messages_after_cut: list   # die behaltenen Messages
    is_split_turn: bool
    turn_prefix_count: int
    previous_summary: str | None
    tokens_before: int


@dataclass
class CompactionResult:
    """Was Hooks zurückgeben können."""
    cancel: bool = False
    summary: str | None = None
    details: dict = field(default_factory=dict)


BeforeFn = Callable[[CompactionContext], Awaitable[Optional[CompactionResult]]]
ExtractFn = Callable[[CompactionContext], Awaitable[dict]]
FlushFn = Callable[[CompactionContext], Awaitable[None]]
SummarizeFn = Callable[[CompactionContext, str], Awaitable[Optional[str]]]
AfterFn = Callable[[CompactionContext, str], Awaitable[None]]


@dataclass
class CompactionHooks:
    name: str
    before_compact: Optional[BeforeFn] = None
    extract_facts: Optional[ExtractFn] = None
    pre_compact_flush: Optional[FlushFn] = None
    custom_summarize: Optional[SummarizeFn] = None
    after_compact: Optional[AfterFn] = None


_REGISTRY: list[CompactionHooks] = []


def register(hooks: CompactionHooks) -> None:
    _REGISTRY.append(hooks)


def all_hooks() -> list[CompactionHooks]:
    return list(_REGISTRY)


async def collect_facts(ctx: CompactionContext) -> dict:
    """Sammle Fakten aus allen registrierten Plugins, Plugin-Name als Key-Prefix."""
    facts: dict[str, Any] = {}
    for h in _REGISTRY:
        if not h.extract_facts:
            continue
        try:
            data = await h.extract_facts(ctx)
            for k, v in (data or {}).items():
                facts[f"{h.name}.{k}"] = v
        except Exception:
            pass
    return facts
