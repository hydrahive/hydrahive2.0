from __future__ import annotations

import pytest

from hydrahive.projects import config as project_config


def _payload(flow_id: str, *, scope: str = "project", scope_id: str | None = "project-1") -> dict:
    return {
        "flow_id": flow_id,
        "name": "Scope Test",
        "enabled": True,
        "scope": scope,
        "scope_id": scope_id,
        "nodes": [],
        "edges": [],
    }


def _project(*, member_role: str | None = None) -> dict:
    members = [] if member_role is None else [{"username": "testuser", "role": member_role}]
    return {
        "id": "project-1",
        "created_by": "bob",
        "members": members,
        "agent_id": "project-agent",
        "allowed_specialists": [],
    }


@pytest.mark.parametrize(
    ("case", "project", "status_code", "error_code"),
    [
        ("foreign", _project(), 403, "project_no_access"),
        ("missing", None, 404, "project_not_found"),
        ("read", _project(member_role="read"), 403, "project_no_access"),
    ],
)
def test_create_flow_lehnt_unzulaessigen_projekt_scope_ab(
    client, auth_headers, monkeypatch, case, project, status_code, error_code,
):
    monkeypatch.setattr(project_config, "get", lambda project_id: project)

    response = client.post(
        "/api/butler/flows",
        headers=auth_headers,
        json=_payload(f"create-scope-{case}"),
    )

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == error_code


def test_project_scope_verlangt_scope_id(client, auth_headers):
    response = client.post(
        "/api/butler/flows",
        headers=auth_headers,
        json=_payload("create-scope-empty", scope_id="  "),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "butler_project_scope_id_required"


def test_create_flow_erlaubt_write_mitglied(client, auth_headers, monkeypatch):
    monkeypatch.setattr(project_config, "get", lambda project_id: _project(member_role="write"))

    response = client.post(
        "/api/butler/flows", headers=auth_headers, json=_payload("create-scope-write"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["scope_id"] == "project-1"


def test_user_scope_verwirft_scope_id(client, auth_headers):
    response = client.post(
        "/api/butler/flows",
        headers=auth_headers,
        json=_payload("create-user-scope", scope="user", scope_id="foreign-project"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["scope_id"] is None


@pytest.mark.parametrize(
    ("case", "project", "status_code"),
    [
        ("foreign", _project(), 403),
        ("missing", None, 404),
        ("read", _project(member_role="read"), 403),
        ("write", _project(member_role="write"), 200),
    ],
)
def test_update_flow_prueft_projekt_schreibrecht(
    client, auth_headers, monkeypatch, case, project, status_code,
):
    flow_id = f"update-scope-{case}"
    created = client.post(
        "/api/butler/flows",
        headers=auth_headers,
        json=_payload(flow_id, scope="user", scope_id=None),
    )
    assert created.status_code == 201, created.text
    monkeypatch.setattr(project_config, "get", lambda project_id: project)

    response = client.put(
        f"/api/butler/flows/{flow_id}", headers=auth_headers, json=_payload(flow_id),
    )

    assert response.status_code == status_code, response.text
