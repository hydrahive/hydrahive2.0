"""Runner: das Herz von HydraHive.

Verbindet Agent-Config + Tools + LLM + Session-DB. Eine `run()` = ein User-Turn
mit beliebig vielen Tool-Iterationen. Persistiert alles, yieldet Events für
spätere SSE-Anbindung.
"""

from hydrahive.runner import events
from hydrahive.runner.events import (
    Done,
    Error,
    Event,
    IterationStart,
    MessageStart,
    TextBlock,
    TextDelta,
    ToolUseResult,
    ToolUseStart,
)
from hydrahive.runner.runner import MAX_ITERATIONS, run

__all__ = [
    "run",
    "MAX_ITERATIONS",
    "events",
    "Event",
    "IterationStart",
    "MessageStart",
    "TextBlock",
    "TextDelta",
    "ToolUseStart",
    "ToolUseResult",
    "Done",
    "Error",
]
