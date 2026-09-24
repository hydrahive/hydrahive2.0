"""Begrenzte Beobachtungssignale ohne persistierte Rohargumente oder Outputs."""
from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from hydrahive.runner.integrity_evidence import (
    EVIDENCE_KINDS,
    completion_claim_kinds,
    effective_tool_success,
    evidence_for_tool,
    missing_evidence_for_claim,
    safe_signal_subject,
    update_evidence_state,
)
from hydrahive.tools.base import ToolResult

_EPHEMERAL_ARGUMENT_KEYS = frozenset({
    "call_id", "request_id", "stream_id", "timestamp", "created_at",
})
_MAX_FINGERPRINT_INPUT = 8_192


@dataclass(frozen=True)
class IntegritySignal:
    kind: str
    level: str
    detail: str
    subject: str | None = None


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _EPHEMERAL_ARGUMENT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def canonical_tool_payload(tool_name: str, arguments: dict[str, Any] | None) -> str:
    """Return deterministic, non-ephemeral tool data for tests/fingerprints."""
    payload = {"name": tool_name, "arguments": _normalize(arguments or {})}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    serialized = json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, default=str)
    serialized = serialized[:_MAX_FINGERPRINT_INPUT]
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]


class IntegrityState:
    """Bounded per-run state. Phase 1 emits signals; it never blocks a run."""

    def __init__(
        self, goal: str | None = None, *, history_limit: int = 64,
        initial_evidence: Iterable[str] = (),
    ) -> None:
        self._goal_digest = _digest(goal or "")
        self._history: deque[tuple[str, str, bool]] = deque(maxlen=max(8, history_limit))
        self._pending_signals: deque[IntegritySignal] = deque(maxlen=max(8, history_limit))
        self._evidence_kinds = set(initial_evidence).intersection(EVIDENCE_KINDS)
        self._continued_evidence = len(self._evidence_kinds)
        if self._continued_evidence:
            self._pending_signals.append(IntegritySignal(
                "evidence_continued", "observe",
                "Evidenz aus direkter Session-Fortsetzung übernommen.",
            ))
        self._seen_result_digests: deque[str] = deque(maxlen=max(16, history_limit * 2))
        self._seen_result_set: set[str] = set()
        self._last_action: str | None = None
        self._last_result: str | None = None
        self._same_action_streak = 0
        self._same_result_streak = 0
        self._error_streak = 0
        self._tool_observations = 0
        self._new_evidence = 0
        self._completion_claims = 0
        self._claim_kinds: set[str] = set()

    def record_tool(
        self, tool_name: str, arguments: dict[str, Any] | None, result: ToolResult,
    ) -> list[IntegritySignal]:
        action_digest = _digest(canonical_tool_payload(tool_name, arguments))
        succeeded = effective_tool_success(tool_name, result)
        result_value = result.output if succeeded else {"error": result.error, "output": result.output}
        result_digest = _digest(result_value)
        if action_digest == self._last_action:
            self._same_action_streak += 1
        else:
            self._same_action_streak = 1
        if result_digest == self._last_result:
            self._same_result_streak += 1
        else:
            self._same_result_streak = 1
        self._error_streak = self._error_streak + 1 if not succeeded else 0
        self._last_action = action_digest
        self._last_result = result_digest
        self._tool_observations += 1
        self._history.append((action_digest, result_digest, succeeded))

        new_evidence = succeeded and result_digest not in self._seen_result_set
        observed_evidence = evidence_for_tool(tool_name, arguments, succeeded=succeeded)
        update_evidence_state(self._evidence_kinds, observed_evidence)
        if new_evidence:
            self._new_evidence += 1
            if len(self._seen_result_digests) == self._seen_result_digests.maxlen:
                self._seen_result_set.discard(self._seen_result_digests[0])
            self._seen_result_digests.append(result_digest)
            self._seen_result_set.add(result_digest)

        signals: list[IntegritySignal] = []
        subject = safe_signal_subject(tool_name)
        if self._same_action_streak == 3:
            signals.append(IntegritySignal(
                "repeated_tool_action", "observe",
                "Dieselbe kanonische Tool-Aktion wurde dreimal wiederholt.", subject,
            ))
        if self._same_result_streak == 3 or self._error_streak == 3:
            signals.append(IntegritySignal(
                "no_progress", "observe",
                "Drei aufeinanderfolgende Tool-Ergebnisse lieferten keine neue Evidenz.", subject,
            ))
        if self._error_streak == 3:
            signals.append(IntegritySignal(
                "error_chain", "observe",
                "Drei aufeinanderfolgende Tool-Aufrufe sind fehlgeschlagen.", subject,
            ))
        self._pending_signals.extend(signals)
        return signals

    def record_assistant_text(self, text: str | None) -> list[IntegritySignal]:
        if not text:
            return []
        signals: list[IntegritySignal] = []
        for kind in completion_claim_kinds(text):
            self._completion_claims += 1
            self._claim_kinds.add(kind)
            signals.append(IntegritySignal(
                "completion_claim", "observe",
                f"Completion-Claim erkannt: {kind}.", kind,
            ))
            missing = missing_evidence_for_claim(kind, self._evidence_kinds)
            if missing:
                signals.append(IntegritySignal(
                    "unverified_completion_claim", "observe",
                    f"Completion-Claim {kind} ohne Evidenz: {', '.join(missing)}.", kind,
                ))
        self._pending_signals.extend(signals)
        return signals

    def record_assistant_blocks(self, blocks: list[dict] | None) -> list[IntegritySignal]:
        """Inspect only visible text blocks, never tool arguments or reasoning."""
        signals: list[IntegritySignal] = []
        for block in blocks or []:
            if isinstance(block, dict) and block.get("type") == "text":
                signals.extend(self.record_assistant_text(block.get("text")))
        return signals

    def drain_signals(self) -> list[dict[str, str]]:
        """Consume pending, bounded signals in JSON-safe audit form."""
        signals = []
        for item in self._pending_signals:
            signal = {"kind": item.kind, "level": item.level, "detail": item.detail}
            if item.subject:
                signal["subject"] = item.subject
            signals.append(signal)
        self._pending_signals.clear()
        return signals

    def audit_metadata(self) -> dict[str, Any]:
        """Return a compact observation record suitable for message metadata."""
        return {
            "mode": "observe",
            "snapshot": self.snapshot(),
            "signals": self.drain_signals(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "goal_present": self._goal_digest != _digest(""),
            "tool_observations": self._tool_observations,
            "unique_actions": len({item[0] for item in self._history}),
            "new_evidence": self._new_evidence,
            "continued_evidence": self._continued_evidence,
            "completion_claims": self._completion_claims,
            "completion_claim_kinds": sorted(self._claim_kinds),
            "evidence_kinds": sorted(self._evidence_kinds),
            "same_action_streak": self._same_action_streak,
            "same_result_streak": self._same_result_streak,
            "error_streak": self._error_streak,
        }
