"""Tests für das create_specialist-Tool (projekt-gebunden, tools-bounded)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.tools import create_specialist as cs
from hydrahive.tools.base import ToolContext


def _ctx():
    return ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))


def test_create_specialist_forces_project_and_subsets_tools(monkeypatch):
    creator = {"id": "proj-agent", "type": "project", "owner": "u",
               "project_id": "P", "llm_model": "claude-sonnet-4-6",
               "tools": ["file_read", "shell_exec", "create_specialist"]}
    created: dict = {}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: creator)
    monkeypatch.setattr("hydrahive.agents.config.create",
                        lambda *a, **k: (created.update(k), {"id": "spec-1", **k})[1])
    monkeypatch.setattr("hydrahive.projects.config.get",
                        lambda pid: {"id": pid, "allowed_specialists": []})
    captured: dict = {}
    monkeypatch.setattr("hydrahive.projects.config.update",
                        lambda pid, **ch: captured.update(ch))

    res = asyncio.run(cs.TOOL.execute(
        {"name": "rust-reviewer",
         "tools": ["file_read", "shell_exec", "create_specialist", "todo_write"]},
        _ctx()))

    assert res.success
    assert created["project_id"] == "P"
    assert created["owner"] == "u"
    assert created["agent_type"] == "specialist"
    assert set(created["tools"]) == {"file_read", "shell_exec"}
    assert "spec-1" in captured["allowed_specialists"]


def test_create_specialist_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "m", "type": "master", "owner": "u"})
    res = asyncio.run(cs.TOOL.execute({"name": "x"}, _ctx()))
    assert not res.success
