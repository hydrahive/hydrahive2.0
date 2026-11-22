"""Wörtliche Kopie des AgentLink-State-Schemas (hydralink ``agentlink/backend/main.py``,
Abschnitt „SCHEMA - Agent State v1“), damit Tests die Payload von ``post_state`` gegen das
echte Empfänger-Modell prüfen können.

Warum Kopie statt Import: ``main.py`` importiert beim Laden FastAPI, SQLAlchemy, Redis und
``database`` (DB-Verbindung). Das gibt es in der Kern-CI nicht. Damit die Kopie nicht
veraltet, vergleicht ``test_agentlink_wire_schema.py::test_kopie_entspricht_agentlink``
die Klassen per AST mit dem Original, sobald ``hydralink-work`` neben dem Repo liegt.
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# fmt: off
# ruff: noqa
class FileContext(BaseModel):
    path: str
    diff: Optional[str] = None
    lines: Optional[tuple[int, int]] = None
    hash: Optional[str] = None  # git blob hash


class GitContext(BaseModel):
    repo: str
    branch: str
    commit: str


class ErrorContext(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None


class Context(BaseModel):
    files: List[FileContext] = []
    git: Optional[GitContext] = None
    errors: List[ErrorContext] = []


class Knowledge(BaseModel):
    amem_ids: List[str] = []
    qmd_refs: List[str] = []
    external_urls: List[str] = []


class Decision(BaseModel):
    what: str
    why: str
    when: datetime


class WorkingMemory(BaseModel):
    hypotheses: List[str] = []
    open_questions: List[str] = []
    decisions: List[Decision] = []
    findings: List[str] = []


class Task(BaseModel):
    type: Literal["bug_fix", "feature", "review", "research", "refactor"]
    description: str
    priority: int = Field(ge=1, le=5)
    status: Literal["pending", "in_progress", "blocked", "done"] = "pending"


class Handoff(BaseModel):
    to_agent: Optional[str] = None
    reason: Optional[str] = None
    required_skills: List[str] = []


class AgentState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task: Task
    context: Context
    knowledge: Knowledge = Knowledge()
    working_memory: WorkingMemory = WorkingMemory()
    handoff: Optional[Handoff] = None
