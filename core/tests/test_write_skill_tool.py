"""Tests für write_skill (Projekt-Bibliothek / Spezialist-Scope)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.tools import write_skill as ws
from hydrahive.tools.base import ToolContext


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_write_skill_defaults_to_project_scope(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    saved: dict = {}

    def _save(skill):
        saved["scope"] = skill.scope
        saved["owner"] = skill.owner
        saved["name"] = skill.name
        return True, ""

    monkeypatch.setattr("hydrahive.skills.save_skill", _save)
    res = asyncio.run(ws.TOOL.execute(
        {"name": "rust-review", "description": "d", "when_to_use": "w", "body": "b"}, _ctx()))
    assert res.success
    assert saved == {"scope": "project", "owner": "P", "name": "rust-review"}


def test_write_skill_agent_scope_requires_project_member(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"}
        return {"id": "spec-x", "type": "specialist", "project_id": "OTHER"}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    res = asyncio.run(ws.TOOL.execute(
        {"name": "x", "description": "d", "when_to_use": "w", "body": "b", "specialist_id": "spec-x"}, _ctx()))
    assert not res.success
