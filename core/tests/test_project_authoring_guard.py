"""Tests für den gemeinsamen Authoring-Guard der Projekt-Tools."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.tools import _project_authoring as pa
from hydrahive.tools.base import ToolContext


def _ctx(agent_id="a"):
    return ToolContext(session_id="s", agent_id=agent_id, user_id="u", workspace=Path("/tmp"))


def test_rejects_non_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "a", "type": "master", "owner": "u"})
    with pytest.raises(pa.AuthoringError):
        pa.resolve_project_agent(_ctx())


def test_rejects_project_agent_without_project_id(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "a", "type": "project", "owner": "u"})
    with pytest.raises(pa.AuthoringError):
        pa.resolve_project_agent(_ctx())


def test_resolves_project_agent(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "a", "type": "project", "owner": "u", "project_id": "P"})
    agent, pid = pa.resolve_project_agent(_ctx())
    assert pid == "P"


def test_bounded_tools_intersects_and_strips_authoring():
    out = pa.bounded_tools(["file_read", "shell_exec", "create_specialist"], ["file_read", "list_skills"])
    assert out == ["file_read"]
