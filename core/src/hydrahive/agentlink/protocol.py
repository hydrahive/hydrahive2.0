"""AgentLink State-Schema (Subset) — 1:1 zu agentlink/backend/main.py.

Wir modellieren nur die Felder die HydraHive aktiv liest/schreibt. Andere
Felder (knowledge-refs, A-MEM-IDs etc.) lassen wir als optional und passthrough.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class TaskBlock(BaseModel):
    type: str  # 'bug_fix' | 'feature' | 'review' | 'research' | 'refactor'
    description: str
    priority: int = 5
    status: str = "in_progress"


class ContextBlock(BaseModel):
    files: list[dict] = Field(default_factory=list)
    git: dict | None = None
    errors: list[str] = Field(default_factory=list)


class WorkingMemory(BaseModel):
    hypotheses: list[dict] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)


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
