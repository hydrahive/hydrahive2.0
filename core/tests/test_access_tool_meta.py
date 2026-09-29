"""Agent-Editor: Werkzeuge zeigen ihre Funktion, Admin fragt Freigaben eines Nutzers ab (Plan Task 4.3)."""
from __future__ import annotations

import json

import pytest

from hydrahive import tools
from hydrahive.access import capabilities, grants
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.tools.base import Tool, ToolResult
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


async def _ok(args, ctx):
    return ToolResult.ok("x")


@pytest.fixture
def ha_tools(tmp_path, monkeypatch):
    cat = capabilities.Catalog.with_core()
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"id": "hay", "name": "HA", "version": "1.0.0", "capabilities": [
        {"id": "hay.control", "label": "Schalten", "default": "admin_only", "tools": ["hay_switch"]}]}))
    cat.register_module(ModuleManifest.load(p))
    monkeypatch.setattr(capabilities, "CATALOG", cat)
    tools.register_module_tools([Tool(name="hay_switch", description="d", schema={}, execute=_ok, module_id="hay")])
    yield
    tools.register_module_tools([])


def test_tool_meta_contains_capability(client, auth_headers, ha_tools):
    meta = {t["name"]: t for t in client.get("/api/agents/_meta/tools", headers=auth_headers).json()}
    assert meta["hay_switch"]["capability"] == "hay.control"
    assert meta["file_read"]["capability"] is None


def test_admin_reads_user_capabilities(client, admin_headers, ha_tools):
    users = client.get("/api/users", headers=admin_headers).json()
    uid = next(u["user_id"] for u in users if u["username"] == "testuser")
    grants.grant("hay.control", "user", uid, "use", actor_id="adm")
    r = client.get("/api/access/users/testuser", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["admin"] is False and data["capabilities"]["hay.control"] == "use"


def test_user_reads_own_capabilities_by_name(client, auth_headers, ha_tools):
    assert client.get("/api/access/users/testuser", headers=auth_headers).status_code == 200


def test_user_cannot_read_other_users(client, auth_headers, ha_tools):
    assert client.get("/api/access/users/admin", headers=auth_headers).status_code == 403


def test_unknown_user_404(client, admin_headers, ha_tools):
    assert client.get("/api/access/users/gibt-es-nicht", headers=admin_headers).status_code == 404
