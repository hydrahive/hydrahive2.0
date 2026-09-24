"""Deterministische Laufzeitsignale für die Agent Integrity Layer.

Phase 1 beobachtet nur. Der State hält keine Rohargumente oder Tool-Ausgaben,
sondern ausschließlich begrenzte Fingerprints und Zähler. Dadurch entstehen
keine neuen Secret- oder Prompt-Cache-Pfade.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from dataclasses import dataclass
from typing import Any

from hydrahive.tools.base import ToolResult

# Diese Felder identifizieren einen Aufruf, nicht seine fachliche Absicht.
_EPHEMERAL_ARGUMENT_KEYS = frozenset({
    "call_id", "request_id", "stream_id", "timestamp", "created_at",
})
_MAX_FINGERPRINT_INPUT = 8_192
_COMPLETION_PATTERNS = {
    "implemented": re.compile(r"\b(?:implementiert|implemented|eingebaut|built)\b", re.I),
    "tested": re.compile(r"\b(?:getestet|tested|test(?:s)? bestanden|tests? grün)\b", re.I),
    "deployed": re.compile(r"\b(?:deployt|deployed|ausgerollt|live geschaltet)\b", re.I),
    "fixed": re.compile(r"\b(?:behoben|gefixt|fixed|repaired)\b", re.I),
    "finished": re.compile(r"\b(?:fertig|erledigt|done|completed)\b", re.I),
}


@dataclass(frozen=True)
class IntegritySignal:
    kind: str
    level: str
    detail: str


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

    def __init__(self, goal: str | None = None, *, history_limit: int = 64) -> None:
        self._goal_digest = _digest(goal or "")
        self._history: deque[tuple[str, str, bool]] = deque(maxlen=max(8, history_limit))
        self._pending_signals: deque[IntegritySignal] = deque(maxlen=max(8, history_limit))
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
        result_value = result.output if result.success else {"error": result.error}
        result_digest = _digest(result_value)
        if action_digest == self._last_action:
            self._same_action_streak += 1
        else:
            self._same_action_streak = 1
        if result_digest == self._last_result:
            self._same_result_streak += 1
        else:
            self._same_result_streak = 1
        self._error_streak = self._error_streak + 1 if not result.success else 0
        self._last_action = action_digest
        self._last_result = result_digest
        self._tool_observations += 1
        self._history.append((action_digest, result_digest, result.success))

        new_evidence = result.success and result_digest not in self._seen_result_set
        if new_evidence:
            self._new_evidence += 1
            if len(self._seen_result_digests) == self._seen_result_digests.maxlen:
                self._seen_result_set.discard(self._seen_result_digests[0])
            self._seen_result_digests.append(result_digest)
            self._seen_result_set.add(result_digest)

        signals: list[IntegritySignal] = []
        if self._same_action_streak == 3:
            signals.append(IntegritySignal(
                "repeated_tool_action", "observe",
                "Dieselbe kanonische Tool-Aktion wurde dreimal wiederholt.",
            ))
        if self._same_result_streak == 3 or self._error_streak == 3:
            signals.append(IntegritySignal(
                "no_progress", "observe",
                "Drei aufeinanderfolgende Tool-Ergebnisse lieferten keine neue Evidenz.",
            ))
        if self._error_streak == 3:
            signals.append(IntegritySignal(
                "error_chain", "observe",
                "Drei aufeinanderfolgende Tool-Aufrufe sind fehlgeschlagen.",
            ))
        self._pending_signals.extend(signals)
        return signals

    def record_assistant_text(self, text: str | None) -> list[IntegritySignal]:
        if not text:
            return []
        signals: list[IntegritySignal] = []
        for kind, pattern in _COMPLETION_PATTERNS.items():
            if pattern.search(text):
                self._completion_claims += 1
                self._claim_kinds.add(kind)
                signals.append(IntegritySignal(
                    "completion_claim", "observe",
                    f"Completion-Claim erkannt: {kind}.",
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
        signals = [
            {"kind": item.kind, "level": item.level, "detail": item.detail}
            for item in self._pending_signals
        ]
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
            "completion_claims": self._completion_claims,
            "completion_claim_kinds": sorted(self._claim_kinds),
            "same_action_streak": self._same_action_streak,
            "same_result_streak": self._same_result_streak,
            "error_streak": self._error_streak,
        }
