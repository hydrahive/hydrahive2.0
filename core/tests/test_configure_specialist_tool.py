"""Tests für configure_specialist (eigenes Projekt, tools-bounded)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.tools import configure_specialist as conf
from hydrahive.tools.base import ToolContext


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_rejects_cross_project_target(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u",
                    "project_id": "P", "tools": ["file_read"]}
        return {"id": "spec-x", "type": "specialist", "project_id": "OTHER"}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    res = asyncio.run(conf.TOOL.execute({"agent_id": "spec-x", "status": "disabled"}, _ctx()))
    assert not res.success


def test_configures_own_project_specialist(monkeypatch):
    def _get(_id):
        if _id == "proj-agent":
            return {"id": "proj-agent", "type": "project", "owner": "u",
                    "project_id": "P", "tools": ["file_read", "shell_exec"]}
        return {"id": "spec-1", "type": "specialist", "project_id": "P"}
    captured: dict = {}
    monkeypatch.setattr("hydrahive.agents.config.get", _get)
    monkeypatch.setattr("hydrahive.agents.config.update",
                        lambda aid, **ch: captured.update({"id": aid, **ch}))
    res = asyncio.run(conf.TOOL.execute(
        {"agent_id": "spec-1", "tools": ["file_read", "todo_write"], "status": "disabled"}, _ctx()))
    assert res.success
    assert captured["id"] == "spec-1"
    assert captured["tools"] == ["file_read"]   # todo_write nicht beim Erzeuger → gefiltert
    assert captured["status"] == "disabled"
