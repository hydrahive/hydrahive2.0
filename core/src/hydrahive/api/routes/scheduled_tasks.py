"""CRUD and control API for persistent Agent/Buddy interval tasks."""
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config
from hydrahive.schedules import db
from hydrahive.schedules.scheduler import request_run

router = APIRouter(prefix="/api/scheduled-tasks", tags=["scheduled-tasks"])
MAX_ACTIVE_TASKS_PER_OWNER = 100


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=8000)
    target_type: str = Field(default="agent", pattern="^(agent|buddy)$")
    target_id: str = Field(default="buddy", min_length=1, max_length=128)
    project_id: str | None = Field(default=None, max_length=128)
    execution_mode: str = Field(default="direct", pattern="^(direct|butler_event)$")
    interval_seconds: int = Field(default=60, ge=10, le=86400)
    enabled: bool = True


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    prompt: str | None = Field(default=None, min_length=1, max_length=8000)
    execution_mode: str | None = Field(default=None, pattern="^(direct|butler_event)$")
    interval_seconds: int | None = Field(default=None, ge=10, le=86400)
    enabled: bool | None = None


def _project(project_id: str | None, auth: tuple[str, str]) -> str:
    username, role = auth
    if not project_id:
        return "user"
    project = project_config.get(project_id)
    if not project:
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
    check_project_access(project, username, role, required="write")
    return "project"


def _target(target_type: str, target_id: str, auth: tuple[str, str]) -> None:
    username, role = auth
    if target_type == "buddy":
        if target_id != "buddy":
            raise coded(status.HTTP_400_BAD_REQUEST, "buddy_target_invalid")
        return
    agent = agent_config.get(target_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    if role != "admin" and agent.get("owner") != username:
        raise coded(status.HTTP_403_FORBIDDEN, "agent_no_access")


def _owned(task_id: str, auth: tuple[str, str]):
    task = db.get(task_id)
    if not task:
        raise coded(status.HTTP_404_NOT_FOUND, "scheduled_task_not_found")
    if auth[1] != "admin" and task.owner != auth[0]:
        raise coded(status.HTTP_403_FORBIDDEN, "scheduled_task_no_access")
    return task


@router.get("")
def list_tasks(auth: Annotated[tuple[str, str], Depends(require_auth)], project_id: str | None = None) -> list[dict]:
    if project_id:
        _project(project_id, auth)
    tasks = db.list_(owner=None if auth[1] == "admin" else auth[0], project_id=project_id)
    return [asdict(task) for task in tasks]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    scope = _project(body.project_id, auth)
    _target(body.target_type, body.target_id, auth)
    if db.count_enabled(auth[0]) >= MAX_ACTIVE_TASKS_PER_OWNER:
        raise coded(status.HTTP_409_CONFLICT, "scheduled_task_limit_reached", limit=MAX_ACTIVE_TASKS_PER_OWNER)
    task = db.create(
        owner=auth[0], scope=scope, project_id=body.project_id,
        target_type=body.target_type, target_id=body.target_id,
        title=body.title.strip(), prompt=body.prompt.strip(),
        execution_mode=body.execution_mode, interval_seconds=body.interval_seconds,
        enabled=body.enabled,
    )
    return asdict(task)


@router.get("/admin/all", dependencies=[Depends(require_admin)])
def admin_tasks() -> list[dict]:
    return [asdict(task) for task in db.list_()]


@router.get("/{task_id}")
def get_task(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return asdict(_owned(task_id, auth))


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _owned(task_id, auth)
    changes = body.model_dump(exclude_unset=True)
    task = db.update(task_id, **changes)
    return asdict(task)  # type: ignore[arg-type]


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> None:
    _owned(task_id, auth)
    db.delete(task_id)


@router.post("/{task_id}/run")
def run_task_now(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    task = _owned(task_id, auth)
    if not request_run(task.task_id):
        raise coded(status.HTTP_409_CONFLICT, "scheduled_task_running")
    return {"queued": True, "task_id": task_id}


@router.get("/{task_id}/runs")
def task_runs(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    _owned(task_id, auth)
    return [asdict(run) for run in db.runs(task_id)]


@router.post("/{task_id}/pause")
def pause_task(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _owned(task_id, auth)
    return asdict(db.update(task_id, enabled=False))  # type: ignore[arg-type]


@router.post("/{task_id}/resume")
def resume_task(task_id: str, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    _owned(task_id, auth)
    return asdict(db.update(task_id, enabled=True))  # type: ignore[arg-type]
