from __future__ import annotations

from types import SimpleNamespace

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware import users
from hydrahive.butler import _scheduled_agent_run as scheduled
from hydrahive.butler.models import TriggerEvent
from hydrahive.db import sessions as sessions_db
from hydrahive.projects import config as project_config
from hydrahive.runner import runner
from hydrahive.runner.events import Done


def _project(role: str | None = "write") -> dict:
    members = [] if role is None else [{"username": "alice", "role": role}]
    return {
        "id": "project-1", "created_by": "bob", "members": members,
        "agent_id": "project-agent", "allowed_specialists": ["specialist-1"],
    }


def _runtime(
    monkeypatch, agents: dict[str, dict | None], project: dict | None = None,
    role: str = "user",
):
    created: list[dict] = []
    calls: list[dict] = []
    monkeypatch.setattr(users, "get_by_username", lambda owner: {
        "username": owner, "user_id": f"id-{owner}", "role": role,
    })
    monkeypatch.setattr(project_config, "get", lambda project_id: project)
    monkeypatch.setattr(agent_config, "get", lambda agent_id: agents.get(agent_id))

    def create(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=f"session-{len(created)}")

    async def run(session_id, user_text, **kwargs):
        calls.append({"session_id": session_id, "user_text": user_text, **kwargs})
        yield Done(message_id="done", iterations=1)

    monkeypatch.setattr(sessions_db, "create", create)
    monkeypatch.setattr(runner, "run", run)
    return created, calls


async def _run(agent_id: str, *, project_id: str | None = None, instruction: str = ""):
    return await scheduled.run_scheduled_agent_actions(
        owner="alice", flow_id="flow-1", flow_name="Test", project_id=project_id,
        event=TriggerEvent(event_type="cron", owner="alice"),
        actions=[{
            "subtype": "agent_reply", "reply_via_agent": agent_id,
            "reply_prefix": instruction,
        }],
    )


@pytest.mark.parametrize("agent_id", ["../bob", "team/bob"])
async def test_ungueltige_agent_id_startet_keinen_lauf(monkeypatch, agent_id):
    created, _ = _runtime(
        monkeypatch, {agent_id: {"id": agent_id, "owner": "alice"}},
    )

    outcome = await _run(agent_id)

    assert created == []
    assert outcome.session_ids == []


async def test_config_id_mismatch_startet_keinen_lauf(monkeypatch):
    created, _ = _runtime(
        monkeypatch, {"wanted": {"id": "different", "owner": "alice"}},
    )

    await _run("wanted")

    assert created == []


@pytest.mark.parametrize(
    "agent",
    [None, {"id": "agent-1", "name": "ohne owner"}],
)
async def test_unbekannter_oder_ownerloser_agent_startet_keinen_lauf(monkeypatch, agent):
    created, _ = _runtime(monkeypatch, {"agent-1": agent})

    await _run("agent-1")

    assert created == []


async def test_ownerloser_agent_startet_auch_fuer_admin_nicht(monkeypatch):
    created, _ = _runtime(
        monkeypatch, {"agent-1": {"id": "agent-1"}}, role="admin",
    )

    await _run("agent-1")

    assert created == []


async def test_fremder_projekt_agent_ohne_flow_projekt_startet_nicht(monkeypatch):
    created, _ = _runtime(
        monkeypatch, {"project-agent": {"id": "project-agent", "owner": "bob"}},
    )

    await _run("project-agent")

    assert created == []


@pytest.mark.parametrize("agent_id", ["project-agent", "specialist-1"])
async def test_write_mitglied_darf_projekt_agent_ausfuehren(monkeypatch, agent_id):
    created, _ = _runtime(
        monkeypatch,
        {agent_id: {"id": agent_id, "owner": "bob"}},
        project=_project("write"),
    )

    await _run(agent_id, project_id="project-1")

    assert created[0]["project_id"] == "project-1"


async def test_entzogene_mitgliedschaft_verhindert_session(monkeypatch, caplog):
    created, _ = _runtime(
        monkeypatch,
        {"agent-alice": {"id": "agent-alice", "owner": "alice"}},
        project=_project(None),
    )

    with caplog.at_level("WARNING", logger=scheduled.__name__):
        outcome = await _run("agent-alice", project_id="project-1")

    assert created == []
    assert outcome.session_ids == []
    assert "Projekt" in caplog.text


async def test_cron_vorgabe_wird_als_extra_system_uebergeben(monkeypatch):
    _, calls = _runtime(
        monkeypatch, {"agent-alice": {"id": "agent-alice", "owner": "alice"}},
    )

    await _run("agent-alice", instruction="Prüfe den Kalender.")

    assert "Prüfe den Kalender." in calls[0]["extra_system"]
    assert "Prüfe den Kalender." not in calls[0]["user_text"]
