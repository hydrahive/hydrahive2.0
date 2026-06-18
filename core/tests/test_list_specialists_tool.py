"""Tests für list_specialists (+ Authoring-Prompt-Hint)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from hydrahive.tools import list_specialists as ls
from hydrahive.tools.base import ToolContext


def test_lists_only_own_project_specialists(monkeypatch):
    monkeypatch.setattr("hydrahive.agents.config.get",
                        lambda _id: {"id": "proj-agent", "type": "project", "owner": "u", "project_id": "P"})
    monkeypatch.setattr("hydrahive.agents.config.list_all", lambda: [
        {"id": "s1", "type": "specialist", "project_id": "P", "name": "A", "tools": []},
        {"id": "s2", "type": "specialist", "project_id": "OTHER", "name": "B", "tools": []},
        {"id": "m", "type": "master", "project_id": None, "name": "M", "tools": []},
    ])
    ctx = ToolContext(session_id="s", agent_id="proj-agent", user_id="u", workspace=Path("/tmp"))
    res = asyncio.run(ls.TOOL.execute({}, ctx))
    assert res.success
    ids = {s["id"] for s in res.output["specialists"]}
    assert ids == {"s1"}


def test_tool_has_authoring_prompt_hint():
    assert ls.TOOL.prompt_hint and "Spezialist" in ls.TOOL.prompt_hint
