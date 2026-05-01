from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class IterationStart:
    """A new iteration of the tool-loop is starting."""
    iteration: int
    type: Literal["iteration_start"] = "iteration_start"


@dataclass
class MessageStart:
    """A new assistant message is starting — UI prepares an empty bubble."""
    type: Literal["message_start"] = "message_start"


@dataclass
class TextDelta:
    """Partial text chunk during streaming — append to current assistant text."""
    text: str
    type: Literal["text_delta"] = "text_delta"


@dataclass
class TextBlock:
    """The assistant produced text. Non-streaming path or final consolidated."""
    text: str
    type: Literal["text"] = "text"


@dataclass
class ToolUseStart:
    """The agent decided to call a tool."""
    call_id: str
    tool_name: str
    arguments: dict
    type: Literal["tool_use_start"] = "tool_use_start"


@dataclass
class ToolConfirmRequired:
    """Tool-Confirm-Modus aktiv — Runner wartet auf User-Entscheidung."""
    call_id: str
    tool_name: str
    arguments: dict
    type: Literal["tool_confirm_required"] = "tool_confirm_required"


@dataclass
class ToolUseResult:
    """A tool finished executing."""
    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int | None = None
    type: Literal["tool_use_result"] = "tool_use_result"


@dataclass
class Done:
    """The turn is complete."""
    message_id: str
    iterations: int
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    type: Literal["done"] = "done"


@dataclass
class Error:
    """A fatal error stopped the run."""
    message: str
    fatal: bool = True
    metadata: dict = field(default_factory=dict)
    type: Literal["error"] = "error"


Event = (
    IterationStart | MessageStart | TextDelta | TextBlock |
    ToolUseStart | ToolConfirmRequired | ToolUseResult | Done | Error
)
