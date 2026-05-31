from __future__ import annotations

from pathlib import Path

from hydrahive.runner.system_prompt import compose


def _compose(allowed):
    stable, _volatile, _summary = compose(
        "BASE",
        extra_system=None,
        workspace=Path("/tmp/ws"),
        summary=None,
        skills=None,
        longterm_memory=False,
        tool_schemas=[],
        allowed_tools=allowed,
    )
    return stable


def test_hint_present_when_tool_allowed():
    stable = _compose(["read_scratchpad", "write_scratchpad"])
    assert "Scratchpad" in stable
    assert "read_scratchpad" in stable


def test_hint_absent_without_tool():
    stable = _compose(["file_read"])
    assert "Scratchpad" not in stable
