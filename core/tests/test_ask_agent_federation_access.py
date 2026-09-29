"""ask_agent → Föderation nur mit Freigabe core.federation (Plan P3, Task 3.4).

Der Föderations-Zweig kannte bisher den Aufrufer nicht. Jetzt prüft er vor jedem
Netzaufruf, ob der Besitzer des Laufs core.federation nutzen darf.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.access import capabilities, grants
from hydrahive.tools import ToolContext
from hydrahive.tools import ask_agent


@pytest.fixture(autouse=True)
def _core_catalog(monkeypatch):
    monkeypatch.setattr(capabilities, "CATALOG", capabilities.Catalog.with_core())


@pytest.fixture
def no_network(monkeypatch):
    calls: list[str] = []

    async def fake_remote_chat(ws_id, task, persona_id=None):
        calls.append(ws_id)
        return "antwort"

    import hydrahive.federation.registry as reg
    import hydrahive.db.federation as fed_db
    monkeypatch.setattr(reg, "remote_chat", fake_remote_chat)
    monkeypatch.setattr(fed_db, "get_by_name", lambda n: {"id": "ws-1", "name": n, "enabled": 1})
    monkeypatch.setattr(fed_db, "get_workstation", lambda n: None)
    return calls


def _ctx(user: str, tmp_path) -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=tmp_path)


def _run(user: str, tmp_path):
    return asyncio.run(ask_agent._execute({"agent_id": "geralt@tillwks", "task": "hi"}, _ctx(user, tmp_path)))


def test_user_without_grant_is_refused_without_network(client, no_network, tmp_path):
    res = _run("testuser", tmp_path)
    assert res.success is False and "Freigabe" in (res.error or "")
    assert no_network == []


def test_admin_may_use_federation(client, no_network, tmp_path):
    res = _run("admin", tmp_path)
    assert res.success is True and no_network == ["ws-1"]


def test_user_with_grant_may_use_federation(client, admin_headers, no_network, tmp_path):
    users = client.get("/api/users", headers=admin_headers).json()
    uid = next(u["user_id"] for u in users if u["username"] == "testuser")
    grants.grant("core.federation", "user", uid, "use", actor_id="adm")
    assert _run("testuser", tmp_path).success is True


def test_unknown_user_is_refused(client, no_network, tmp_path):
    res = _run("gibt-es-nicht", tmp_path)
    assert res.success is False and no_network == []
