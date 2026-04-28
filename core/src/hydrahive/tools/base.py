from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable


@dataclass
class ToolContext:
    """Runtime context every tool gets — caller (Runner) builds this."""
    session_id: str
    agent_id: str
    user_id: str
    workspace: Path
    config: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any = None, **metadata: Any) -> "ToolResult":
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "ToolResult":
        return cls(success=False, error=error, metadata=metadata)

    def to_llm(self) -> str:
        """Render the result as text for the LLM."""
        if not self.success:
            return f"FEHLER: {self.error}"
        if self.output is None:
            return "OK"
        if isinstance(self.output, str):
            return self.output
        import json
        return json.dumps(self.output, indent=2, ensure_ascii=False)


ExecuteFn = Callable[[dict, ToolContext], Awaitable[ToolResult]]


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    execute: ExecuteFn
