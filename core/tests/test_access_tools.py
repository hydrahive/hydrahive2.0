"""Werkzeug-Filter und Dispatcher-Prüfung (Plan P4, Tasks 4.1, 4.2).

Agenten erben die Rechte ihres Besitzers (Spec §7 Regel 6): Ein Werkzeug, dessen
Funktion der Besitzer nicht nutzen darf, wird nicht angeboten und bei Aufruf
abgelehnt.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from hydrahive import tools
from hydrahive.access import capabilities, grants
from hydrahive.access.tool_filter import filter_tools, tool_denied
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import ToolContext
from hydrahive.tools.base import Tool, ToolResult
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


async def _ok(args, ctx):
    return ToolResult.ok("geschaltet")


@pytest.fixture
def ha_module(tmp_path, monkeypatch):
    cat = capabilities.Catalog.with_core()
    p = tmp_path / "ha.json"
    p.write_text(json.dumps({"id": "hax", "name": "HA", "version": "1.0.0", "capabilities": [
        {"id": "module.hax", "label": "HA", "default": "everyone"},
        {"id": "hax.control", "label": "Schalten", "default": "admin_only", "tools": ["hax_switch"]},
    ]}))
    cat.register_module(ModuleManifest.load(p))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    switch = Tool(name="hax_switch", description="d", schema={}, execute=_ok, module_id="hax")
    listing = Tool(name="hax_list", description="d", schema={}, execute=_ok, module_id="hax")
    tools.register_module_tools([switch, listing])
    yield
    tools.register_module_tools([])


def _uid(client, admin_headers, name="testuser"):
    users = client.get("/api/users", headers=admin_headers).json()
    return next(u["user_id"] for u in users if u["username"] == name)


def test_register_module_tools_keeps_module_id(client, ha_module):
    assert tools.REGISTRY["hax_switch"].module_id == "hax"


def test_filter_removes_tool_without_grant(client, ha_module):
    grants.grant("module.hax", "everyone", "", "use", actor_id="adm")
    kept = filter_tools("testuser", ["hax_switch", "hax_list", "file_read"])
    assert kept == ["hax_list", "file_read"]


def test_filter_keeps_everything_for_admin(client, ha_module):
    assert filter_tools("admin", ["hax_switch", "hax_list"]) == ["hax_switch", "hax_list"]


def test_filter_keeps_tool_with_grant(client, admin_headers, ha_module):
    grants.grant("module.hax", "everyone", "", "use", actor_id="adm")
    grants.grant("hax.control", "user", _uid(client, admin_headers), "use", actor_id="adm")
    assert filter_tools("testuser", ["hax_switch"]) == ["hax_switch"]


def test_filter_leaves_unknown_and_core_tools(client, ha_module):
    # shell_exec hängt seit Task 3bd963b2 an core.shell (test_access_core_shell.py).
    assert filter_tools("testuser", ["file_read", "mcp__x__y", "gibt_es_nicht"]) == [
        "file_read", "mcp__x__y", "gibt_es_nicht"]


def test_tool_denied_names_capability(client, ha_module):
    assert tool_denied("testuser", "hax_switch") == "hax.control"
    assert tool_denied("admin", "hax_switch") is None
    assert tool_denied("testuser", "file_read") is None


def test_dispatcher_refuses_tool_without_grant(client, ha_module, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="testuser", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="testuser", workspace=tmp_path)
    use = {"id": "tu1", "name": "hax_switch", "input": {}}

    result, _rec, _ms = asyncio.run(execute_tool(use, ["hax_switch"], ctx, msg.id))

    assert result.success is False
    assert "Freigabe" in (result.error or "") and "hax.control" in (result.error or "")


def test_dispatcher_runs_tool_for_admin(client, ha_module, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id="admin", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="admin", workspace=tmp_path)
    use = {"id": "tu2", "name": "hax_switch", "input": {}}

    result, _rec, _ms = asyncio.run(execute_tool(use, ["hax_switch"], ctx, msg.id))

    assert result.success is True
