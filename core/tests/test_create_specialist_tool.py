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
         "tools": ["file_read", "shell_exec", "create_specialist", "todo_write"],
         "max_iterations": 64, "max_tokens": 24_000,
         "compact_threshold_pct": 70, "handoff_timeout_seconds": 1_200},
        _ctx()))

    assert res.success
    assert created["project_id"] == "P"
    assert created["owner"] == "u"
    assert created["agent_type"] == "specialist"
    assert set(created["tools"]) == {"file_read", "shell_exec"}
    assert created["max_iterations"] == 64
    assert created["max_tokens"] == 24_000
    assert created["compact_threshold_pct"] == 70
    assert created["handoff_timeout_seconds"] == 1_200
    assert res.output["max_iterations"] == 64
    assert res.output["handoff_timeout_seconds"] == 1_200
    assert "spec-1" in captured["allowed_specialists"]
    assert {"max_iterations", "max_tokens", "handoff_timeout_seconds"}.issubset(
        cs.TOOL.schema["properties"]
    )


def test_default_specialist_tools_are_also_bounded_by_creator(monkeypatch):
    creator = {
        "id": "proj-agent", "type": "project", "owner": "u", "project_id": "P",
        "llm_model": "claude-sonnet-4-6", "tools": ["fetch_url", "create_specialist"],
    }
    created: dict = {}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: creator)
    monkeypatch.setattr(
        "hydrahive.agents.config.create",
        lambda *args, **kwargs: (created.update(kwargs), {"id": "spec-1", **kwargs})[1],
    )
    monkeypatch.setattr(
        "hydrahive.projects.config.get",
        lambda pid: {"id": pid, "allowed_specialists": ["spec-1"]},
    )

    res = asyncio.run(cs.TOOL.execute({"name": "bounded-defaults"}, _ctx()))

    assert res.success
    assert created["tools"] == ["fetch_url"]


def test_create_specialist_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "m", "type": "master", "owner": "u"})
    res = asyncio.run(cs.TOOL.execute({"name": "x"}, _ctx()))
    assert not res.success
