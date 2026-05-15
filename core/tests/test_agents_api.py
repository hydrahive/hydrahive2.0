"""Agent CRUD API Tests.

Abgedeckt:
- GET  /api/agents        (list)
- GET  /api/agents/{id}   (get)
- POST /api/agents        (create, admin-only)
- PATCH /api/agents/{id}  (update, admin-only)
- DELETE /api/agents/{id} (delete, admin-only)
- GET/PUT /{id}/system_prompt
"""
from __future__ import annotations

import pytest

from tests.conftest import error_code

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

_CREATE_PAYLOAD = {
    "type": "specialist",
    "name": "Test Bot",
    "llm_model": "claude-haiku-4-5-20251001",
}


def _create_agent(client, admin_headers, **overrides) -> dict:
    payload = {**_CREATE_PAYLOAD, **overrides}
    res = client.post("/api/agents", headers=admin_headers, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# GET /api/agents  — list
# ---------------------------------------------------------------------------

def test_list_agents_requires_auth(client):
    res = client.get("/api/agents")
    assert res.status_code == 401


def test_list_agents_user_sees_own(client, auth_headers, admin_headers):
    # Admin erstellt Agent mit owner=testuser
    agent = _create_agent(client, admin_headers, name="User Agent", owner="testuser")

    res = client.get("/api/agents", headers=auth_headers)
    assert res.status_code == 200
    ids = [a["id"] for a in res.json()]
    assert agent["id"] in ids


def test_list_agents_admin_sees_all(client, admin_headers):
    _create_agent(client, admin_headers, name="Admin-owned Bot")

    res = client.get("/api/agents", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


# ---------------------------------------------------------------------------
# GET /api/agents/{id}  — get single
# ---------------------------------------------------------------------------

def test_get_agent_not_found(client, auth_headers):
    res = client.get("/api/agents/does-not-exist", headers=auth_headers)
    assert res.status_code == 404
    assert error_code(res) == "agent_not_found"


def test_get_agent_forbidden_for_other_user(client, auth_headers, admin_headers):
    # Admin erstellt Agent der ihm gehört
    agent = _create_agent(client, admin_headers, name="Admin Private Bot", owner="admin")

    # testuser darf nicht zugreifen
    res = client.get(f"/api/agents/{agent['id']}", headers=auth_headers)
    assert res.status_code == 403
    assert error_code(res) == "agent_no_access"


def test_get_agent_success(client, auth_headers, admin_headers):
    agent = _create_agent(client, admin_headers, name="Accessible Bot", owner="testuser")

    res = client.get(f"/api/agents/{agent['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == agent["id"]
    assert res.json()["name"] == "Accessible Bot"


# ---------------------------------------------------------------------------
# POST /api/agents  — create
# ---------------------------------------------------------------------------

def test_create_agent_requires_admin(client, auth_headers):
    res = client.post("/api/agents", headers=auth_headers, json=_CREATE_PAYLOAD)
    assert res.status_code == 403


def test_create_agent_requires_auth(client):
    res = client.post("/api/agents", json=_CREATE_PAYLOAD)
    assert res.status_code == 401


def test_create_agent_success(client, admin_headers):
    res = client.post("/api/agents", headers=admin_headers, json={
        **_CREATE_PAYLOAD,
        "name": "Fresh Bot",
        "description": "A freshly created bot",
        "temperature": 0.5,
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Fresh Bot"
    assert data["description"] == "A freshly created bot"
    assert data["temperature"] == 0.5
    assert "id" in data


def test_create_agent_missing_required_fields(client, admin_headers):
    res = client.post("/api/agents", headers=admin_headers, json={"type": "specialist"})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/agents/{id}  — update
# ---------------------------------------------------------------------------

def test_patch_agent_requires_admin(client, auth_headers, admin_headers):
    agent = _create_agent(client, admin_headers, name="Patchable Bot")

    res = client.patch(f"/api/agents/{agent['id']}", headers=auth_headers, json={"name": "Hacked"})
    assert res.status_code == 403


def test_patch_agent_not_found(client, admin_headers):
    res = client.patch("/api/agents/ghost-id", headers=admin_headers, json={"name": "X"})
    assert res.status_code == 404
    assert error_code(res) == "agent_not_found"


def test_patch_agent_updates_field(client, admin_headers):
    agent = _create_agent(client, admin_headers, name="Old Name")

    res = client.patch(f"/api/agents/{agent['id']}", headers=admin_headers, json={"name": "New Name"})
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"


def test_patch_agent_exclude_unset_preserves_other_fields(client, admin_headers):
    """Nur explizit gesendete Felder werden geändert (exclude_unset fix)."""
    agent = _create_agent(client, admin_headers, name="Stable Bot", temperature=0.3)

    # Nur name patchen — temperature darf sich nicht ändern
    res = client.patch(f"/api/agents/{agent['id']}", headers=admin_headers, json={"name": "Renamed"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Renamed"
    assert data["temperature"] == pytest.approx(0.3)


def test_patch_agent_empty_body_returns_agent(client, admin_headers):
    agent = _create_agent(client, admin_headers, name="Untouched Bot")

    res = client.patch(f"/api/agents/{agent['id']}", headers=admin_headers, json={})
    assert res.status_code == 200
    assert res.json()["id"] == agent["id"]


# ---------------------------------------------------------------------------
# DELETE /api/agents/{id}  — delete
# ---------------------------------------------------------------------------

def test_delete_agent_requires_admin(client, auth_headers, admin_headers):
    agent = _create_agent(client, admin_headers, name="Deletable Bot")

    res = client.delete(f"/api/agents/{agent['id']}", headers=auth_headers)
    assert res.status_code == 403


def test_delete_agent_not_found(client, admin_headers):
    res = client.delete("/api/agents/nonexistent", headers=admin_headers)
    assert res.status_code == 404
    assert error_code(res) == "agent_not_found"


def test_delete_agent_success(client, admin_headers):
    agent = _create_agent(client, admin_headers, name="Bot to Delete")
    agent_id = agent["id"]

    res = client.delete(f"/api/agents/{agent_id}", headers=admin_headers)
    assert res.status_code == 204

    # Nach dem Löschen nicht mehr abrufbar
    res = client.get(f"/api/agents/{agent_id}", headers=admin_headers)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET/PUT /api/agents/{id}/system_prompt
# ---------------------------------------------------------------------------

def test_get_system_prompt_not_found(client, admin_headers):
    res = client.get("/api/agents/ghost/system_prompt", headers=admin_headers)
    assert res.status_code == 404


def test_set_and_get_system_prompt(client, admin_headers):
    agent = _create_agent(client, admin_headers, name="Prompted Bot")
    agent_id = agent["id"]

    # Setzen
    res = client.put(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers,
                     json={"prompt": "Du bist ein hilfreicher Assistent."})
    assert res.status_code == 200
    assert res.json()["prompt"] == "Du bist ein hilfreicher Assistent."

    # Lesen
    res = client.get(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["prompt"] == "Du bist ein hilfreicher Assistent."
