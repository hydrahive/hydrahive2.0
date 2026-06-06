"""Unit-Tests für die Agent-Tools des Tasks-Moduls."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from hydrahive.db import init_db
from hydrahive.tools.base import ToolContext


def make_ctx(username: str = "alice", session_id: str = "sess-1") -> ToolContext:
    return ToolContext(
        session_id=session_id,
        agent_id="agent-1",
        user_id=username,
        workspace=Path("/tmp"),
    )


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    from hydrahive.db.connection import db
    with db() as c:
        c.execute("DELETE FROM module_tasks")
    yield


# ── task_write ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_write_creates_task():
    from backend.tools.task_write import TOOL
    result = await TOOL.execute({"title": "Testen", "priority": "high"}, make_ctx())
    assert result.success
    assert result.output["created"] is True
    assert result.output["task"]["title"] == "Testen"
    assert result.output["task"]["priority"] == "high"
    assert result.output["task"]["status"] == "open"


@pytest.mark.asyncio
async def test_task_write_updates_existing():
    from backend.tools.task_write import TOOL
    r1 = await TOOL.execute({"title": "Initial"}, make_ctx())
    task_id = r1.output["task"]["id"]

    r2 = await TOOL.execute({"task_id": task_id, "status": "done", "title": "Erledigt"}, make_ctx())
    assert r2.success
    assert r2.output["updated"] is True
    assert r2.output["task"]["status"] == "done"
    assert r2.output["task"]["title"] == "Erledigt"


@pytest.mark.asyncio
async def test_task_write_invalid_task_id():
    from backend.tools.task_write import TOOL
    r = await TOOL.execute({"task_id": "nonexistent", "title": "X"}, make_ctx())
    assert not r.success


@pytest.mark.asyncio
async def test_task_write_inherits_project_from_ctx():
    from backend.tools.task_write import TOOL
    ctx = make_ctx()
    ctx.project_id = "my-project"
    r = await TOOL.execute({"title": "Mit Projekt"}, ctx)
    assert r.output["task"]["project_id"] == "my-project"


# ── task_list ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_list_empty():
    from backend.tools.task_list import TOOL
    r = await TOOL.execute({}, make_ctx())
    assert r.success
    assert r.output["count"] == 0


@pytest.mark.asyncio
async def test_task_list_returns_created_tasks():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    ctx = make_ctx()
    await write.execute({"title": "Eins"}, ctx)
    await write.execute({"title": "Zwei"}, ctx)

    r = await lst.execute({}, ctx)
    assert r.output["count"] == 2
    titles = [t["title"] for t in r.output["tasks"]]
    assert "Eins" in titles
    assert "Zwei" in titles


@pytest.mark.asyncio
async def test_task_list_filter_by_status():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    ctx = make_ctx()
    r = await write.execute({"title": "Offen"}, ctx)
    task_id = r.output["task"]["id"]
    await write.execute({"task_id": task_id, "status": "done"}, ctx)
    await write.execute({"title": "Noch offen"}, ctx)

    r = await lst.execute({"status": "open"}, ctx)
    assert r.output["count"] == 1
    assert r.output["tasks"][0]["title"] == "Noch offen"


@pytest.mark.asyncio
async def test_task_list_user_isolation():
    from backend.tools.task_write import TOOL as write
    from backend.tools.task_list import TOOL as lst
    await write.execute({"title": "Alices Task"}, make_ctx("alice"))
    await write.execute({"title": "Bobs Task"},   make_ctx("bob"))

    alice_result = await lst.execute({}, make_ctx("alice"))
    assert alice_result.output["count"] == 1
    assert alice_result.output["tasks"][0]["title"] == "Alices Task"
