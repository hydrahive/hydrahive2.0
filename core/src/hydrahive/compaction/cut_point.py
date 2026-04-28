from __future__ import annotations

from dataclasses import dataclass

from hydrahive.compaction.tokens import estimate_message
from hydrahive.db.messages import Message


@dataclass
class CutPoint:
    """Result of finding where to compact.

    `kept_from_index` — first index in the message list that will be kept.
    Messages [0:kept_from_index] get summarized.
    `is_split_turn` — true if cutting mid-turn (single huge turn exceeds budget).
    `turn_prefix_count` — when split, number of pre-cut messages from the same
    turn that should be summarized as 'turn prefix'.
    """
    kept_from_index: int
    is_split_turn: bool = False
    turn_prefix_count: int = 0


def find_cut_point(messages: list[Message], keep_recent_tokens: int) -> CutPoint:
    """Walk backwards from newest, accumulate tokens until budget reached.

    Cut rules:
      - Valid cut points: user / assistant messages
      - Never cut at tool_result (must stay with its tool_use)
      - When a single turn exceeds budget → split-turn at an assistant message
    """
    if not messages:
        return CutPoint(kept_from_index=0)

    cumulative = 0
    cut_index = len(messages)  # default: keep everything
    for i in range(len(messages) - 1, -1, -1):
        cumulative += estimate_message(messages[i])
        if cumulative > keep_recent_tokens:
            cut_index = i + 1
            break
    else:
        return CutPoint(kept_from_index=0)

    # Adjust: never cut so that a tool_result becomes the first kept message
    while cut_index < len(messages) and _is_tool_results_only(messages[cut_index]):
        cut_index += 1

    if cut_index >= len(messages):
        # Single huge turn: split at last assistant inside the turn
        return _split_turn(messages, keep_recent_tokens)

    return CutPoint(kept_from_index=cut_index)


def _is_tool_results_only(message: Message) -> bool:
    """True if the message only carries tool_result blocks (paired with prior assistant)."""
    if message.role != "user":
        return False
    if not isinstance(message.content, list) or not message.content:
        return False
    return all(
        isinstance(b, dict) and b.get("type") == "tool_result"
        for b in message.content
    )


def _split_turn(messages: list[Message], keep_recent_tokens: int) -> CutPoint:
    """Single turn exceeds budget. Cut at an assistant message inside the turn."""
    turn_start = _find_turn_start(messages, len(messages) - 1)

    cumulative = 0
    last_assistant_split = len(messages)
    for i in range(len(messages) - 1, turn_start, -1):
        cumulative += estimate_message(messages[i])
        if messages[i].role == "assistant" and cumulative <= keep_recent_tokens:
            last_assistant_split = i

    if last_assistant_split <= turn_start:
        last_assistant_split = turn_start

    turn_prefix_count = max(0, last_assistant_split - turn_start)
    return CutPoint(
        kept_from_index=last_assistant_split,
        is_split_turn=turn_prefix_count > 0,
        turn_prefix_count=turn_prefix_count,
    )


def _find_turn_start(messages: list[Message], from_idx: int) -> int:
    for i in range(from_idx, -1, -1):
        if messages[i].role == "user" and not _is_tool_results_only(messages[i]):
            return i
    return 0
