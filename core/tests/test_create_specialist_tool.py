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

    assert res.success, res.error
    assert created["project_id"] == "P"
    assert created["owner"] == "u"
    assert created["agent_type"] == "specialist"
    assert set(created["tools"]) == {"file_read", "shell_exec"}
    assert created["template"] == "reviewer"     # aus dem Namen (Aufräumen 14.11.2026)
    assert "spec-1" in captured["allowed_specialists"]
    assert not {"max_iterations", "max_tokens", "handoff_timeout_seconds", "llm_model"} & set(
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


def _fake_env(monkeypatch, created: dict):
    creator = {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P",
               "llm_model": "claude-sonnet-4-6", "tools": ["file_read"]}
    monkeypatch.setattr("hydrahive.agents.config.get", lambda _id: creator)
    monkeypatch.setattr("hydrahive.agents.config.create",
                        lambda *a, **k: (created.update(k), {"id": "spec-1", **k})[1])
    monkeypatch.setattr("hydrahive.projects.config.get", lambda pid: {"id": pid, "allowed_specialists": []})
    monkeypatch.setattr("hydrahive.projects.config.update", lambda pid, **ch: None)


def test_create_specialist_mit_template(monkeypatch):
    """Agenten-Templates (Plan E3 T5): Template wird an create durchgereicht."""
    created: dict = {}
    _fake_env(monkeypatch, created)
    res = asyncio.run(cs.TOOL.execute({"name": "rev", "template": "reviewer"}, _ctx()))
    assert res.success and created["template"] == "reviewer"
    assert "template" in cs.TOOL.schema["properties"]


def test_create_specialist_template_und_modell_abgelehnt(monkeypatch):
    created: dict = {}
    _fake_env(monkeypatch, created)
    res = asyncio.run(cs.TOOL.execute({"name": "rev", "llm_model": "x", "max_iterations": 9}, _ctx()))
    assert not res.success and "llm_model" in res.error and "max_iterations" in res.error
    assert created == {}
