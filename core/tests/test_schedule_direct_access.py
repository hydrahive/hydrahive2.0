"""Direkte Intervallaufgaben prüfen Rechte bei JEDER Ausführung.

Zweite Sicherheitsprüfung (01.10.2026, KRITISCH): Projekt- und Agentrechte
wurden nur beim Anlegen geprüft (api/routes/scheduled_tasks.py). Nach Entzug
der Projektmitgliedschaft lief eine Aufgabe weiter im Projekt-Workspace.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from hydrahive.schedules import execution
from hydrahive.schedules.models import ScheduledTask


def _task(**over) -> ScheduledTask:
    base = dict(
        task_id="task-d", owner="alice", scope="project", project_id="project-1",
        target_type="agent", target_id="agent-alice", title="Intervall", prompt="Prompt",
        execution_mode="direct", interval_seconds=60, enabled=True, running=True,
        next_run_at="2026-06-05T10:02:00+00:00", last_run_at=None,
        last_status="running", last_error=None, failure_count=0,
        created_at="2026-06-05T10:00:00+00:00", updated_at="2026-06-05T10:00:00+00:00",
    )
    base.update(over)
    return ScheduledTask(**base)


@pytest.fixture
def runtime(monkeypatch):
    state = {"created": [], "finished": [], "project_ok": True,
             "agents": {"agent-alice": {"id": "agent-alice", "owner": "alice"},
                        "agent-bob": {"id": "agent-bob", "owner": "bob"}}}

    def project_access(project_id, owner, role):
        if not state["project_ok"]:
            raise HTTPException(403, "project_no_access")
        return {"id": project_id, "agent_id": "proj-agent", "allowed_specialists": []}

    monkeypatch.setattr(execution, "assert_project_access", project_access)
    monkeypatch.setattr(execution.agent_config, "get", lambda aid: state["agents"].get(aid))
    monkeypatch.setattr(execution, "_owner_role", lambda owner: "user")
    monkeypatch.setattr(execution.sessions_db, "create",
                        lambda **kw: state["created"].append(kw) or SimpleNamespace(id="s-1"))
    monkeypatch.setattr(execution.db, "finish",
                        lambda *a, **kw: state["finished"].append(kw))

    async def no_run(*a, **kw):
        if False:
            yield None
    monkeypatch.setattr(execution.runner, "run", no_run)
    return state


async def test_entzogene_projektmitgliedschaft_stoppt_direkte_aufgabe(runtime):
    runtime["project_ok"] = False
    await execution._run_direct_task(_task(), "run-1")
    assert runtime["created"] == []
    assert runtime["finished"][-1]["status"] == "failed"
    assert "Projekt" in runtime["finished"][-1]["error"]


async def test_fremder_agent_stoppt_direkte_aufgabe(runtime):
    await execution._run_direct_task(_task(target_id="agent-bob"), "run-1")
    assert runtime["created"] == []
    assert runtime["finished"][-1]["status"] == "failed"


@pytest.mark.parametrize("bad", ["../x", "a/b", "", "agent-alice "])
async def test_ungueltige_agent_id_stoppt_direkte_aufgabe(runtime, bad):
    # Selbst wenn ein (manipulierter) Loader zu jeder ID eine passende
    # Config liefert, darf eine Pfad-ID nie bis zur Session kommen.
    runtime["agents"][bad] = {"id": bad, "owner": "alice"}
    await execution._run_direct_task(_task(target_id=bad), "run-1")
    assert runtime["created"] == []
    assert runtime["finished"][-1]["error"] == "Ungültige Agent-ID"


async def test_berechtigte_aufgabe_laeuft(runtime):
    await execution._run_direct_task(_task(), "run-1")
    assert runtime["created"][0]["project_id"] == "project-1"
    assert runtime["finished"][-1]["status"] == "succeeded"
