"""GET /api/agents/{id}/knowledge – Sicht eines Agenten für den Bereich „Wissen“ (knowledge-spaces.md §2.4)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch


def _make(owner: str, name: str, tools=None, agent_type="specialist", project_id=None):
    from hydrahive.agents import config as ac
    return ac.create(agent_type=agent_type, name=name, llm_model="claude-sonnet-5", tools=tools or [], owner=owner,
                     created_by="x", project_id=project_id, temperature=0.7, max_tokens=1000, thinking_budget=0)


def test_nur_admin(client, auth_headers):
    a = _make("testuser", "k1")
    assert client.get(f"/api/agents/{a['id']}/knowledge", headers=auth_headers).status_code == 403


def test_unbekannter_agent_404(client, admin_headers):
    assert client.get("/api/agents/gibtsnicht/knowledge", headers=admin_headers).status_code == 404


def test_sicht_aussenwirkung_und_zaehler(client, admin_headers):
    a = _make("testuser", "k2", tools=["shell_exec", "file_read"], project_id="P1")
    with patch("hydrahive.api.routes.agent_knowledge._count", AsyncMock(return_value=42)) as count:
        r = client.get(f"/api/agents/{a['id']}/knowledge", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["effective"] == {"scope": "project", "projects": ["P1"], "max_level": "normal", "group_users": []}
    assert body["limited_by_outward_tools"] is True and body["outward_tools"] == ["shell_exec"]
    assert body["visible_events"] == 42 and body["counted_for"] == "testuser"
    sc = count.call_args.args[0]
    assert sc.username == "testuser" and sc.projects == ("P1",)     # gezählt mit der Sicht des Besitzers


def test_ohne_datamining_kein_zaehler(client, admin_headers):
    a = _make("testuser", "k3")
    with patch("hydrahive.db._mirror_search._pool", return_value=None):
        r = client.get(f"/api/agents/{a['id']}/knowledge", headers=admin_headers)
    assert r.status_code == 200 and r.json()["visible_events"] is None


def test_master_ist_nicht_begrenzt(client, admin_headers):
    a = _make("testuser", "k4", tools=["shell_exec"], agent_type="master")
    with patch("hydrahive.api.routes.agent_knowledge._count", AsyncMock(return_value=None)):
        body = client.get(f"/api/agents/{a['id']}/knowledge", headers=admin_headers).json()
    assert body["limited_by_outward_tools"] is False and body["effective"]["max_level"] == "gesundheit"
