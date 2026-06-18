"""Tests für delete_skill (Projekt-/Spezialist-Scope)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.tools import delete_skill_tool as dst
from hydrahive.tools.base import ToolContext


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_delete_project_skill(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    deleted: dict = {}
    monkeypatch.setattr(
        "hydrahive.skills.delete_skill",
        lambda scope, owner, name: (deleted.update({"scope": scope, "owner": owner, "name": name}), True)[1],
    )
    res = asyncio.run(dst.TOOL.execute({"name": "rust-review"}, _ctx()))
    assert res.success
    assert deleted == {"scope": "project", "owner": "P", "name": "rust-review"}


def test_delete_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "m", "type": "master", "owner": "u"})
    res = asyncio.run(dst.TOOL.execute({"name": "x"}, _ctx()))
    assert not res.success
