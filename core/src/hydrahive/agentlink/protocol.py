"""AgentLink State-Schema (Subset) — 1:1 zu agentlink/backend/main.py.

Wir modellieren nur die Felder die HydraHive aktiv liest/schreibt. Andere
Felder (knowledge-refs, A-MEM-IDs etc.) lassen wir als optional und passthrough.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator


class TaskBlock(BaseModel):
    type: str  # 'bug_fix' | 'feature' | 'review' | 'research' | 'refactor'
    description: str
    priority: int = 5
    status: str = "in_progress"


class ErrorEntry(BaseModel):
    """Ein Eintrag in ``context.errors``, wie AgentLink ihn verlangt (``ErrorContext``).

    Bis 21.11.2026 schickte HydraHive hier Text. AgentLink lehnte jeden State mit
    nicht-leerer Liste mit 422 ab (Task 54c50a91: Spezialisten „auf Abruf“ und
    Budget-Überschreitung unerreichbar)."""
    type: str
    message: str
    stack: str | None = None


def error_entry(kind: str, value: Any) -> ErrorEntry:
    """Text, dict oder ErrorEntry → ErrorEntry. Text bekommt ``type=kind``."""
    if isinstance(value, ErrorEntry):
        return value
    if isinstance(value, dict) and isinstance(value.get("message"), str):
        stack = value.get("stack")
        return ErrorEntry(type=str(value.get("type") or kind), message=value["message"],
                          stack=stack if isinstance(stack, str) else None)
    return ErrorEntry(type=kind, message=value if isinstance(value, str) else str(value))


class ContextBlock(BaseModel):
    files: list[dict] = Field(default_factory=list)
    git: dict | None = None
    errors: list[ErrorEntry] = Field(default_factory=list)

    @field_validator("errors", mode="before")
    @classmethod
    def _errors_als_objekte(cls, value: Any) -> Any:
        # Alte Aufrufer und gespeicherte States mit Text-Einträgen bleiben gültig.
        if isinstance(value, (list, tuple)):
            return [error_entry("hint", v) for v in value]
        return value

    def error_lines(self) -> list[str]:
        """Hinweise als Textzeilen für den Empfänger (handoff_receiver)."""
        return [e.message if isinstance(e, ErrorEntry) else str(e) for e in self.errors]


class WorkingMemory(BaseModel):
    hypotheses: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class Handoff(BaseModel):
    to_agent: str
    reason: str
    required_skills: list[str] = Field(default_factory=list)
    # Korrelations-ID damit wir Antwort-States dem ursprünglichen Aufrufer
    # zuordnen können. Wir hängen sie hier rein, AgentLink ignoriert unbekannte
    # Felder im handoff-Block nicht — daher als separates Reply-Marker
    # transportieren wir es über required_skills oder reason. Nutzen wir die
    # state.id als Korrelation: Antwort-State referenziert via reason
    # \"reply_to:<state-id>\".


class State(BaseModel):
    """AgentLink-State-Objekt für POST /states und WS-Events."""
    agent_id: str
    task: TaskBlock
    context: ContextBlock = Field(default_factory=ContextBlock)
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    handoff: Handoff | None = None
    # AgentLink ergänzt id, created_at automatisch beim Insert
    id: str | None = None
    created_at: str | None = None
    knowledge: dict | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


# WebSocket-Push-Event (z.B. handoff_received)
class WSEvent(BaseModel):
    type: str
    state_id: str | None = None
    to_agent: str | None = None
    from_agent: str | None = None
    timestamp: str | None = None
    # Restliche Felder als raw durchreichen
    raw: dict[str, Any] = Field(default_factory=dict)
