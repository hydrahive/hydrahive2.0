from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.scratchpad import service
from hydrahive.tools import read_scratchpad, write_scratchpad
from hydrahive.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return ToolContext(
        session_id="s1", agent_id="a1", user_id="u1", workspace=Path(tmp_path)
    )


def test_read_returns_both_zones(ctx):
    service.save_user("u1", "IDEE-A")
    service.save_agent("u1", "NOTIZ-B")
    result = asyncio.run(read_scratchpad.TOOL.execute({}, ctx))
    assert result.success
    assert "IDEE-A" in result.output
    assert "NOTIZ-B" in result.output


def test_write_only_touches_agent_zone(ctx):
    service.save_user("u1", "TILLS TEXT")
    result = asyncio.run(write_scratchpad.TOOL.execute({"content": "agent neu"}, ctx))
    assert result.success
    assert service.get_agent("u1") == "agent neu"
    assert service.get_user("u1") == "TILLS TEXT"  # unangetastet


def test_write_rejects_non_string(ctx):
    result = asyncio.run(write_scratchpad.TOOL.execute({"content": 123}, ctx))
    assert not result.success


def test_tools_registered():
    from hydrahive.tools import REGISTRY
    assert "read_scratchpad" in REGISTRY
    assert "write_scratchpad" in REGISTRY


def test_master_has_scratchpad_tools():
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    assert "read_scratchpad" in DEFAULT_TOOLS["master"]
    assert "write_scratchpad" in DEFAULT_TOOLS["master"]
