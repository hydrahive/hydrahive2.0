"""Katalog Auftrag 6b (Backend): Review-Punkte aus #786 und Admin-Route für Kategorie-Bestätigungen (KO3, KO4).

Pool-, Freigabe- und Bestätigungsänderungen landen im vorhandenen Audit-Log (``access_audit``, ``access.store``).
"""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import pytest

from tests._own_rows import only_own_rows

from hydrahive.agentlink.protocol import State, TaskBlock
from hydrahive.agents import config as agent_config
from hydrahive.tools import REGISTRY, ToolContext, ask_agent
from hydrahive.tools.base import Tool, ToolResult

sys.path.insert(0, str(Path(__file__).parent))

TABLES = ("owner_tool_grants", "agent_tool_pools", "project_tool_pools", "tool_category_approvals", "access_audit")
MODEL = "claude-sonnet-4-6"


@pytest.fixture(autouse=True)
def _sauber(setup_test_env):
    from hydrahive.db import init_db
    init_db()
    with only_own_rows(*TABLES):
        yield


@pytest.fixture
def made(client):
    created: list[str] = []

    def make(name: str, owner: str = "testuser", tools=None) -> dict:
        a = agent_config.create(agent_type="specialist", name=name, llm_model=MODEL, owner=owner,
                                tools=list(tools if tools is not None else ["file_read"]),
                                temperature=0.7, max_tokens=1000, thinking_budget=0)
        created.append(a["id"])
        return a

    yield make
    for aid in created:
        agent_config.delete(aid)


async def _noop(args, ctx):
    return ToolResult.ok("x")


def _tool(name: str, category: str = "media") -> Tool:
    return Tool(name=name, description=name, schema={"type": "object", "properties": {}}, execute=_noop,
                category=category, module_id="mod1")


def _audit(target: str) -> list[str]:
    from hydrahive.access.store import audit_for
    return [r["action"] for r in audit_for(target)]


# ── KO4 ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_ablehnungstext_nennt_nur_abgelehnte_namen(made, monkeypatch, tmp_path):
    from hydrahive.agents import tool_pools
    monkeypatch.setattr(ask_agent.settings, "agentlink_url", "http://agentlink.test", raising=False)
    monkeypatch.setattr(ask_agent.settings, "agentlink_agent_id", "hydrahive", raising=False)

    async def boom(state: State) -> State:
        raise AssertionError("nichts darf beauftragt werden")
    monkeypatch.setattr(ask_agent, "post_state", boom, raising=False)
    ziel = made("Ziel-6b")
    tool_pools.set_agent_pool("admin", ziel["id"], ["file_read", "web_search"])
    ctx = ToolContext(session_id="s", agent_id="x", user_id="testuser", workspace=tmp_path)
    res = asyncio.run(ask_agent._execute({"goal": "g", "deliverable": "d", "agent_id": ziel["id"], "task": "t",
                                          "tools": ["web_search", "shell_exec"]}, ctx))
    assert res.success is False and "shell_exec" in res.error
    assert "file_read" not in res.error and "web_search" not in res.error      # weder Pool noch Erlaubtes


def test_tool_grants_unbekannter_nutzer_404(client, admin_headers):
    r = client.get("/api/admin/tool-grants/gibt-es-nicht-6b", headers=admin_headers)
    assert r.status_code == 404
    assert client.get("/api/admin/tool-grants/testuser", headers=admin_headers).status_code == 200


def test_tool_pools_py_unter_200_zeilen_und_remove_ausgelagert():
    from hydrahive.agents import _tool_pool_cleanup, tool_pools
    assert len(inspect.getsource(tool_pools).splitlines()) < 200
    for name in ("remove_agent", "remove_project", "remove_user"):
        assert callable(getattr(_tool_pool_cleanup, name))


def test_bounded_tools_loest_kategorien_des_erzeugers_auf():
    from hydrahive.tools._project_authoring import bounded_tools
    assert bounded_tools(["file_read", "web_search"], ["kategorie:files"]) == ["file_read"]
    assert bounded_tools(["create_specialist", "file_write"], ["kategorie:files", "create_specialist"]) == ["file_write"]


def test_harness_doctor_zaehlt_ueber_effective_tool_names(made):
    from hydrahive.harness_doctor.collector import _agent_metrics
    from hydrahive.catalog.categories import resolve_categories
    a = made("Doctor-6b", tools=["kategorie:files", "web_search"])
    row = _agent_metrics(agent_config.get(a["id"]), {})
    expected = len(resolve_categories(["kategorie:files", "web_search"]))
    assert row["configured_tools"] == expected and expected > 2
    assert row["tool_schemas"] == expected                      # Schemas der aufgelösten Tools, nicht des Rohnamens


# ── KO3: Admin-Route Kategorie-Bestätigungen ─────────────────────────────────────────────────────────────────────

def test_admin_route_bestaetigen_widerrufen_mit_audit(client, admin_headers, monkeypatch):
    from hydrahive.catalog.categories import resolve_categories
    monkeypatch.setitem(REGISTRY, "mod_bildchen_6b", _tool("mod_bildchen_6b"))
    assert "mod_bildchen_6b" not in resolve_categories(["kategorie:media"])
    r = client.post("/api/admin/tool-categories", headers=admin_headers,
                    json={"category": "media", "tool": "mod_bildchen_6b", "approved_by": "jemand-anders"})
    assert r.status_code == 200
    assert "mod_bildchen_6b" in resolve_categories(["kategorie:media"])
    listing = client.get("/api/admin/tool-categories", headers=admin_headers).json()
    row = [a for a in listing["approvals"] if a["tool"] == "mod_bildchen_6b"]
    assert row and row[0]["approved_by"] == "admin"             # Identität aus dem Token, nicht aus dem Body
    assert client.delete("/api/admin/tool-categories/media/mod_bildchen_6b", headers=admin_headers).status_code == 200
    assert "mod_bildchen_6b" not in resolve_categories(["kategorie:media"])
    assert client.delete("/api/admin/tool-categories/media/mod_bildchen_6b", headers=admin_headers).status_code == 404
    assert _audit("tool_category:media") == ["tool_category_approve", "tool_category_revoke"]


def test_admin_route_nur_fuer_admin_und_pruefungen(client, auth_headers, admin_headers, monkeypatch):
    monkeypatch.setitem(REGISTRY, "mod_x_6b", _tool("mod_x_6b", category="files"))
    body = {"category": "media", "tool": "mod_x_6b"}
    assert client.post("/api/admin/tool-categories", headers=auth_headers, json=body).status_code == 403
    assert client.get("/api/admin/tool-categories", headers=auth_headers).status_code == 403
    assert client.delete("/api/admin/tool-categories/media/mod_x_6b", headers=auth_headers).status_code == 403
    assert client.post("/api/admin/tool-categories", headers=admin_headers, json=body).status_code == 400   # falsche Kategorie
    assert _audit("tool_category:media") == []


def test_revoke_funktion_nur_admin():
    from hydrahive.catalog import categories
    with pytest.raises(PermissionError):
        categories.revoke("media", "irgendwas", "testuser")


def test_pool_und_freigabe_landen_im_audit(client, admin_headers, auth_headers, made, projekt_6b):
    a = made("Audit-6b")
    assert client.put("/api/admin/tool-grants/testuser", headers=admin_headers, json={"items": ["file_read"]}).status_code == 200
    assert client.put(f"/api/agents/{a['id']}/tool-pool", headers=auth_headers, json={"items": ["file_read"]}).status_code == 200
    assert client.put(f"/api/projects/{projekt_6b['id']}/tool-pool", headers=admin_headers, json={"items": ["file_read"]}).status_code == 200
    assert "tool_grants_set" in _audit("user:testuser")
    assert _audit(f"agent:{a['id']}") == ["tool_pool_set"]
    assert _audit(f"project:{projekt_6b['id']}") == ["tool_pool_set"]
    # Abgelehntes landet nicht im Audit
    assert client.put(f"/api/agents/{a['id']}/tool-pool", headers=auth_headers, json={"items": ["web_search"]}).status_code == 403
    assert _audit(f"agent:{a['id']}") == ["tool_pool_set"]


@pytest.fixture
def projekt_6b(client):
    from hydrahive.projects import config as project_config
    p = project_config.create(name="audit-6b", llm_model=MODEL, created_by="admin", members=[])
    yield p
    try:
        project_config.delete(p["id"])
    except Exception:                                   # noqa: BLE001 — Aufräumen
        pass
