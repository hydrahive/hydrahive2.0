from __future__ import annotations

from types import SimpleNamespace

import pytest

from hydrahive import buddy
from hydrahive.agents import config as agent_config
from hydrahive.butler import executor, scheduler
from hydrahive.butler.models import Edge, Flow, Node, NodePosition
from hydrahive.butler.registry import load_builtins
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner
from hydrahive.runner.events import Done, Error
from hydrahive.schedules import execution
from hydrahive.schedules.models import ScheduledTask

load_builtins()


def _flow(*, trigger: str, trigger_params: dict, agent_id: str,
          action: str = "agent_reply", instruction: str = "",
          reply_text: str = "", owner: str = "alice") -> Flow:
    params = {"agent_id": agent_id}
    if instruction:
        params["instruction"] = instruction
    if reply_text:
        params["text"] = reply_text
    return Flow(
        flow_id="flow-1", name="Morgenroutine", owner=owner, enabled=True,
        nodes=[
            Node(id="trigger", type="trigger", subtype=trigger,
                 position=NodePosition(x=0, y=0), params=trigger_params),
            Node(id="action", type="action", subtype=action,
                 position=NodePosition(x=100, y=0), params=params),
        ],
        edges=[Edge(id="edge", source="trigger", target="action")],
    )


def _task() -> ScheduledTask:
    return ScheduledTask(
        task_id="task-1", owner="alice", scope="user", project_id=None,
        target_type="buddy", target_id="buddy", title="Intervall",
        prompt="Nicht als Agent-Prompt verwenden", execution_mode="butler_event",
        interval_seconds=60, enabled=True, running=True,
        next_run_at="2026-06-05T10:02:00+00:00", last_run_at=None,
        last_status="running", last_error=None, failure_count=0,
        created_at="2026-06-05T10:00:00+00:00",
        updated_at="2026-06-05T10:00:00+00:00",
    )


def _runtime(monkeypatch, *, agent_owner: str = "alice", error: str | None = None):
    calls: list[dict] = []
    created: list[dict] = []

    monkeypatch.setattr(
        buddy, "get_or_create_buddy",
        lambda owner: {"agent_id": "buddy-alice", "session_id": "lifetime"},
    )
    monkeypatch.setattr(
        agent_config, "get",
        lambda agent_id: {"id": agent_id, "owner": agent_owner},
    )

    def create_session(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=f"session-{len(created)}")

    async def run_agent(session_id, user_text, **kwargs):
        calls.append({"session_id": session_id, "user_text": user_text, **kwargs})
        if error:
            yield Error(error)
        else:
            yield Done(message_id="done", iterations=1)

    monkeypatch.setattr(sessions_db, "create", create_session)
    monkeypatch.setattr(runner, "run", run_agent)
    return calls, created


async def test_schedule_event_startet_agent_in_neuer_owner_session(monkeypatch):
    flow = _flow(
        trigger="heartbeat_fired", trigger_params={"task_id": "task-1"},
        agent_id="master", action="agent_reply_with_prefix",
        instruction="Prüfe zuerst den Kalender.",
    )
    monkeypatch.setattr(executor.bp, "list_flows", lambda owner=None: [flow])
    calls, created = _runtime(monkeypatch)
    finishes: list[dict] = []
    monkeypatch.setattr(execution.db, "finish", lambda *args, **kw: finishes.append(kw))

    await execution.run_task(_task(), "run-1")

    assert len(calls) == 1
    assert created == [{
        "agent_id": "buddy-alice", "user_id": "alice", "project_id": None,
        "title": "Automatisch: Morgenroutine",
        "metadata": {"flow_id": "flow-1", "schedule_id": "task-1"},
    }]
    assert "Prüfe zuerst den Kalender." in calls[0]["extra_system"]
    assert "Prüfe zuerst den Kalender." not in calls[0]["user_text"]
    assert calls[0]["user_text"].startswith("Geplanter Butler-Ablauf ‚Morgenroutine‘ ausgelöst um ")
    assert "origin" not in calls[0]
    assert finishes == [{"status": "succeeded", "session_id": "session-1"}]


async def test_cron_event_startet_agent_in_neuer_owner_session(monkeypatch):
    flow = _flow(
        trigger="cron_fired", trigger_params={"cron": "* * * * *"},
        agent_id="agent-alice",
    )
    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [flow])
    calls, created = _runtime(monkeypatch)

    fired = await scheduler._tick(
        scheduler.datetime(2026, 6, 5, 10, 0, tzinfo=scheduler.timezone.utc),
        scheduler.datetime(2026, 6, 5, 10, 1, tzinfo=scheduler.timezone.utc),
    )

    assert fired == 1
    assert len(calls) == 1
    assert created[0]["user_id"] == "alice"
    assert created[0]["metadata"] == {"flow_id": "flow-1", "schedule_id": None}
    assert calls[0]["user_text"] == (
        "Geplanter Butler-Ablauf ‚Morgenroutine‘ ausgelöst um "
        "2026-06-05T10:01:00+00:00."
    )


async def test_fremder_agent_wird_nicht_ausgefuehrt(monkeypatch, caplog):
    flow = _flow(
        trigger="cron_fired", trigger_params={"cron": "* * * * *"},
        agent_id="agent-bob",
    )
    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [flow])
    calls, created = _runtime(monkeypatch, agent_owner="bob")

    with caplog.at_level("WARNING", logger="hydrahive.butler._scheduled_agent_run"):
        await scheduler._tick(
            scheduler.datetime(2026, 6, 5, 10, 0, tzinfo=scheduler.timezone.utc),
            scheduler.datetime(2026, 6, 5, 10, 1, tzinfo=scheduler.timezone.utc),
        )

    assert calls == []
    assert created == []
    assert "fremden Agent" in caplog.text


async def test_admin_darf_fremden_agent_ausfuehren(monkeypatch):
    flow = _flow(
        trigger="cron_fired", trigger_params={"cron": "* * * * *"},
        agent_id="agent-bob", owner="admin",
    )
    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [flow])
    calls, created = _runtime(monkeypatch, agent_owner="bob")

    await scheduler._tick(
        scheduler.datetime(2026, 6, 5, 10, 0, tzinfo=scheduler.timezone.utc),
        scheduler.datetime(2026, 6, 5, 10, 1, tzinfo=scheduler.timezone.utc),
    )

    assert len(calls) == 1
    assert created[0]["user_id"] == "admin"


async def test_reply_text_bleibt_bei_cron_im_trace(monkeypatch, caplog):
    flow = _flow(
        trigger="cron_fired", trigger_params={"cron": "* * * * *"},
        agent_id="", action="reply_fixed", reply_text="Kein externer Kanal",
    )
    monkeypatch.setattr(scheduler.bp, "list_flows", lambda owner=None: [flow])
    calls, created = _runtime(monkeypatch)

    with caplog.at_level("INFO", logger="hydrahive.butler._scheduled_agent_run"):
        await scheduler._tick(
            scheduler.datetime(2026, 6, 5, 10, 0, tzinfo=scheduler.timezone.utc),
            scheduler.datetime(2026, 6, 5, 10, 1, tzinfo=scheduler.timezone.utc),
        )

    assert calls == []
    assert created == []
    assert "reply_text" in caplog.text


async def test_agent_fehler_markiert_schedule_lauf_als_failed(monkeypatch):
    flow = _flow(
        trigger="heartbeat_fired", trigger_params={"task_id": "task-1"},
        agent_id="agent-alice",
    )
    monkeypatch.setattr(executor.bp, "list_flows", lambda owner=None: [flow])
    _runtime(monkeypatch, error="LLM nicht erreichbar")
    finishes: list[dict] = []
    monkeypatch.setattr(execution.db, "finish", lambda *args, **kw: finishes.append(kw))

    await execution.run_task(_task(), "run-1")

    assert finishes == [{
        "status": "failed", "session_id": "session-1",
        "error": "LLM nicht erreichbar",
    }]
