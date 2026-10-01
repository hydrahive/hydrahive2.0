from __future__ import annotations

import asyncio
from types import SimpleNamespace

from hydrahive.schedules import execution
from hydrahive.schedules.models import ScheduledTask


def _task() -> ScheduledTask:
    return ScheduledTask(
        task_id="task-1", owner="alice", scope="user", project_id=None,
        target_type="buddy", target_id="buddy", title="Intervall", prompt="Prompt",
        execution_mode="butler_event", interval_seconds=60, enabled=True, running=True,
        next_run_at="2026-06-05T10:02:00+00:00", last_run_at=None,
        last_status="running", last_error=None, failure_count=0,
        created_at="2026-06-05T10:00:00+00:00",
        updated_at="2026-06-05T10:00:00+00:00",
    )


def _result(flow_id: str) -> dict:
    return {
        "owner": "alice", "flow_id": flow_id, "flow_name": flow_id,
        "actions_executed": [],
    }


async def test_mehrere_flows_laufen_trotz_einzelner_exception(monkeypatch):
    monkeypatch.setattr(
        execution.butler_executor, "dispatch_event",
        lambda *args, **kwargs: None,
    )

    async def dispatch_event(*args, **kwargs):
        return [_result("broken"), _result("working")]

    calls: list[str] = []

    async def run_actions(**kwargs):
        calls.append(kwargs["flow_id"])
        if kwargs["flow_id"] == "broken":
            raise RuntimeError("Flow explodiert")
        return SimpleNamespace(session_ids=["session-2"], errors=[])

    finishes: list[dict] = []
    monkeypatch.setattr(execution.butler_executor, "dispatch_event", dispatch_event)
    monkeypatch.setattr(execution, "run_scheduled_agent_actions", run_actions)
    monkeypatch.setattr(execution.db, "finish", lambda *args, **kwargs: finishes.append(kwargs))

    await execution.run_task(_task(), "run-1")

    assert calls == ["broken", "working"]
    assert finishes[-1]["status"] == "failed"
    assert finishes[-1]["session_id"] == "session-2"
    assert "Flow explodiert" in finishes[-1]["error"]


async def test_agent_pruefung_verwendet_projekt_des_flows(monkeypatch):
    result = {**_result("project-flow"), "project_id": "flow-project"}

    async def dispatch_event(*args, **kwargs):
        return [result]

    seen_projects: list[str | None] = []

    async def run_actions(**kwargs):
        seen_projects.append(kwargs["project_id"])
        return SimpleNamespace(session_ids=[], errors=[])

    monkeypatch.setattr(execution.butler_executor, "dispatch_event", dispatch_event)
    monkeypatch.setattr(execution, "run_scheduled_agent_actions", run_actions)
    monkeypatch.setattr(execution.db, "finish", lambda *args, **kwargs: None)

    await execution.run_task(_task(), "run-1")

    assert seen_projects == ["flow-project"]


async def test_schedule_ausfuehrung_wird_nach_zeitlimit_abgebrochen(monkeypatch):
    cancelled = asyncio.Event()

    async def dispatch_event(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    finishes: list[dict] = []
    monkeypatch.setattr(execution, "_RUN_TIMEOUT_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(execution.butler_executor, "dispatch_event", dispatch_event)
    monkeypatch.setattr(execution.db, "finish", lambda *args, **kwargs: finishes.append(kwargs))

    await asyncio.wait_for(execution.run_task(_task(), "run-1"), timeout=0.2)

    assert cancelled.is_set()
    assert finishes[-1]["status"] == "failed"
    assert "Zeitlimit" in finishes[-1]["error"]
