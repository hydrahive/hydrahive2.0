"""core.shell: Server-Zugriff nur für Admins oder mit Freigabe (Task 3bd963b2).

Befund 29.09.2026: shell_exec läuft als Dienst-User ohne Sandbox und kann
Schlüssel und Nutzerdaten des Servers lesen. web_browser liest file:// und
erreicht 127.0.0.1. Die Plugins file-search, code-metrics und git-stats nehmen
Pfade ohne Workspace-Grenze. Ein Risiko, eine Freigabe: core.shell deckt alle
diese Werkzeuge ab und startet admin_only.
"""
from __future__ import annotations

import asyncio

import pytest

from hydrahive.access import capabilities, grants
from hydrahive.access.bootstrap import apply_defaults
from hydrahive.access.tool_filter import filter_tools, tool_denied
from hydrahive.db import messages as messages_db
from hydrahive.db import sessions as sessions_db
from hydrahive.plugins import tool_bridge
from hydrahive.runner.dispatcher import execute_tool
from hydrahive.tools import ToolContext
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)

SERVER_TOOLS = ["shell_exec", "web_browser", "plugin__file-search__grep"]


@pytest.fixture(autouse=True)
def _core_catalog(monkeypatch):
    monkeypatch.setattr(capabilities, "CATALOG", capabilities.Catalog.with_core())


def _uid(client, admin_headers, name="testuser"):
    users = client.get("/api/users", headers=admin_headers).json()
    return next(u["user_id"] for u in users if u["username"] == name)


# --- Katalog --------------------------------------------------------------

def test_core_shell_is_declared_admin_only():
    cap = capabilities.catalog().get("core.shell")
    assert cap.default == "admin_only" and cap.module_id == ""
    assert {"shell_exec", "web_browser"} <= set(cap.tools)


@pytest.mark.parametrize("tool", SERVER_TOOLS)
def test_server_tools_map_to_core_shell(tool):
    assert capabilities.catalog().capability_for_tool(tool, module_id="") == "core.shell"


@pytest.mark.parametrize("tool", ["file_read", "file_write", "fetch_url", "ask_agent", "mcp__x__y"])
def test_other_core_tools_stay_unmapped(tool):
    assert capabilities.catalog().capability_for_tool(tool, module_id="") is None


def test_module_tool_named_like_core_tool_is_not_captured():
    """Die Core-Zuordnung gilt nur für Core-Werkzeuge (module_id leer)."""
    assert capabilities.catalog().capability_for_tool("shell_exec", module_id="somemod") is None


# --- Filter + Dispatcher --------------------------------------------------

def test_user_without_grant_loses_server_tools(client):
    kept = filter_tools("testuser", [*SERVER_TOOLS, "file_read"])
    assert kept == ["file_read"]


def test_admin_keeps_server_tools(client):
    assert filter_tools("admin", SERVER_TOOLS) == SERVER_TOOLS


def test_grant_unlocks_all_server_tools(client, admin_headers):
    grants.grant("core.shell", "user", _uid(client, admin_headers), "use", actor_id="adm")
    assert filter_tools("testuser", SERVER_TOOLS) == SERVER_TOOLS


def test_unknown_run_owner_is_refused(client):
    assert tool_denied("gibt-es-nicht", "shell_exec") == "core.shell"


def _dispatch(tool: str, user: str, tmp_path):
    s = sessions_db.create(agent_id="a1", user_id=user, title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id=user, workspace=tmp_path)
    use = {"id": f"tu-{tool}", "name": tool, "input": {"cmd": "echo nie"}}
    return asyncio.run(execute_tool(use, [tool], ctx, msg.id))[0]


def test_dispatcher_refuses_shell_without_grant(client, tmp_path, monkeypatch):
    ran: list[str] = []

    async def fake_run(*a, **k):
        ran.append("lief")
        raise AssertionError("darf nicht laufen")

    from hydrahive.tools import _launcher
    monkeypatch.setattr(_launcher.get_launcher(), "run", fake_run, raising=False)
    result = _dispatch("shell_exec", "testuser", tmp_path)
    assert result.success is False and "core.shell" in (result.error or "")
    assert ran == []


def test_dispatcher_refuses_plugin_without_grant(client, tmp_path, monkeypatch):
    called: list[str] = []

    async def fake_call(name, args, ctx):
        called.append(name)
        raise AssertionError("darf nicht laufen")

    monkeypatch.setattr(tool_bridge, "call", fake_call)
    result = _dispatch("plugin__file-search__grep", "testuser", tmp_path)
    assert result.success is False and "core.shell" in (result.error or "")
    assert called == []


# --- Anfangszustand + Anzeige ---------------------------------------------

def test_bootstrap_creates_no_everyone_grant_for_core_shell(client):
    apply_defaults()
    assert grants.grants_for("core.shell") == []


@pytest.fixture
def fake_plugin(monkeypatch):
    """Ein geladenes Plugin mit einem Werkzeug (im Test gibt es sonst keine)."""
    from hydrahive.plugins import registry
    from hydrahive.tools.base import Tool, ToolResult

    async def _ok(args, ctx):
        return ToolResult.ok("x")

    plugin = registry.LoadedPlugin(
        name="probe", manifest=None, module=object(),
        tools=[Tool(name="look", description="d", schema={}, execute=_ok)],
    )
    monkeypatch.setitem(registry.REGISTRY, "probe", plugin)
    return "plugin__probe__look"


def test_tool_meta_marks_server_tools(client, auth_headers, fake_plugin):
    meta = {t["name"]: t for t in client.get("/api/agents/_meta/tools", headers=auth_headers).json()}
    assert meta["shell_exec"]["capability"] == "core.shell"
    assert meta["web_browser"]["capability"] == "core.shell"
    assert meta["file_read"]["capability"] is None
    assert meta[fake_plugin]["capability"] == "core.shell"
