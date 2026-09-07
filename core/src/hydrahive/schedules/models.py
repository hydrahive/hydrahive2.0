"""Types for persistent agent and Buddy interval tasks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExecutionMode = Literal["direct", "butler_event"]
TargetType = Literal["agent", "buddy"]


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    task_id: str
    owner: str
    scope: str
    project_id: str | None
    target_type: TargetType
    target_id: str
    title: str
    prompt: str
    execution_mode: ExecutionMode
    interval_seconds: int
    enabled: bool
    running: bool
    next_run_at: str
    last_run_at: str | None
    last_status: str
    last_error: str | None
    failure_count: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ScheduledRun:
    run_id: str
    task_id: str
    started_at: str
    finished_at: str | None
    status: str
    session_id: str | None
    error: str | None
