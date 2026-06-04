from __future__ import annotations

from pathlib import Path

from hydrahive.runner.system_prompt import compose
from hydrahive.tools.base import Tool, ToolResult


async def _noop(args, ctx):
    return ToolResult.ok("x")


def _compose(allowed):
    stable, _v, _s = compose(
        "BASE", extra_system=None, workspace=Path("/tmp/ws"), summary=None,
        skills=None, longterm_memory=False, tool_schemas=[], allowed_tools=allowed,
    )
    return stable


def test_prompt_hint_injected_when_tool_allowed(monkeypatch):
    fake = Tool(name="faketool", description="d", schema={}, execute=_noop,
                prompt_hint="\n\nFAKE-HINT-XYZ")
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool", fake)
    assert "FAKE-HINT-XYZ" in _compose(["faketool"])


def test_prompt_hint_absent_when_tool_not_allowed(monkeypatch):
    fake = Tool(name="faketool", description="d", schema={}, execute=_noop,
                prompt_hint="\n\nFAKE-HINT-XYZ")
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool", fake)
    assert "FAKE-HINT-XYZ" not in _compose(["file_read"])


def test_tool_without_hint_adds_nothing(monkeypatch):
    fake = Tool(name="faketool2", description="d", schema={}, execute=_noop)
    from hydrahive.tools import REGISTRY
    monkeypatch.setitem(REGISTRY, "faketool2", fake)
    out = _compose(["faketool2"])
    assert "FAKE-HINT" not in out
