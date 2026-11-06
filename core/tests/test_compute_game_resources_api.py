from __future__ import annotations

import hashlib

import pytest

from hydrahive.api.middleware import users
from hydrahive.compute import audit
from hydrahive.compute import db as node_db
from hydrahive.db._utils import uuid7
from tests.conftest import error_code


@pytest.fixture
def game_api_context(client, admin_headers, monkeypatch):
    node_id = f"game-api-{uuid7()}"
    node_db.create_node(
        node_id=node_id,
        name=f"Game API {uuid7()}",
        certificate_fingerprint=hashlib.sha256(node_id.encode()).hexdigest(),
    )
    node_db.approve_node(node_id, users.get_by_username("admin")["user_id"])
    node_db.transition_node_status(node_id, "online")

    approval_response = client.post(
        "/api/compute/game-isolation-approvals",
        headers=admin_headers,
        json={
            "node_id": node_id,
            "isolation_profile_id": "linux-microvm-v1",
            "runner_version": "1.0.0",
            "policy_digest": "sha256:policy-api",
            "proof_digest": "sha256:proof-api",
        },
    )
    assert approval_response.status_code == 201, approval_response.text
    approval = approval_response.json()

    project_id = f"project-{uuid7()}"
    project = {
        "id": project_id,
        "created_by": "another-user",
        "status": "active",
        "members": [],
    }
    from hydrahive.projects import config as project_config

    monkeypatch.setattr(project_config, "get", lambda candidate: project if candidate == project_id else None)
    return {"node_id": node_id, "approval": approval, "project": project, "project_id": project_id}


def _resource_body(context, *, handle: str = "opaque-api-handle", path: str = ".") -> dict:
    approval = context["approval"]
    return {
        "node_id": context["node_id"],
        "workspace_handle": handle,
        "engine": "godot",
        "engine_version": "4.5.1",
        "engine_project_relpath": path,
        "trust_mode": "sandboxed",
        "isolation_approval_id": approval["approval_id"],
        "isolation_profile_id": approval["isolation_profile_id"],
        "runner_version": approval["runner_version"],
        "policy_digest": approval["policy_digest"],
    }


def test_isolation_approval_api_requires_system_admin_and_audits_immutable_user_id(
    client,
    auth_headers,
    admin_headers,
    game_api_context,
) -> None:
    denied = client.get("/api/compute/game-isolation-approvals", headers=auth_headers)
    assert denied.status_code == 403
    assert error_code(denied) == "admin_only"

    allowed = client.get("/api/compute/game-isolation-approvals", headers=admin_headers)
    assert allowed.status_code == 200
    assert any(item["approval_id"] == game_api_context["approval"]["approval_id"] for item in allowed.json())

    record = next(
        item
        for item in audit.list_records(node_id=game_api_context["node_id"])
        if item["action"] == "game.isolation_approval.approved"
    )
    assert record["actor"] == users.get_by_username("admin")["user_id"]
    assert record["actor"] != "admin"


@pytest.mark.parametrize("project_role", [None, "read", "write"])
def test_binding_create_requires_project_admin_and_returns_project_no_access(
    client,
    auth_headers,
    game_api_context,
    project_role,
) -> None:
    project = game_api_context["project"]
    project["members"] = [] if project_role is None else [{"username": "testuser", "role": project_role}]

    response = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
        json=_resource_body(game_api_context),
    )

    assert response.status_code == 403
    assert error_code(response) == "project_no_access"


def test_binding_api_stores_browser_handle_pending_and_scopes_reads_by_project(
    client,
    auth_headers,
    game_api_context,
) -> None:
    project = game_api_context["project"]
    project["members"] = [{"username": "testuser", "role": "admin"}]
    created = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
        json=_resource_body(game_api_context),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["created_by"] == users.get_by_username("testuser")["user_id"]

    project["members"] = [{"username": "testuser", "role": "read"}]
    listed = client.get(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert [item["resource_id"] for item in listed.json()] == [body["resource_id"]]

    missing_project = client.get(
        f"/api/compute/projects/missing-project/game-resources/{body['resource_id']}",
        headers=auth_headers,
    )
    assert missing_project.status_code == 404
    assert error_code(missing_project) == "project_not_found"


def test_binding_rotation_rechecks_project_admin_and_increments_generation(
    client,
    auth_headers,
    game_api_context,
) -> None:
    project = game_api_context["project"]
    project["members"] = [{"username": "testuser", "role": "admin"}]
    created = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
        json=_resource_body(game_api_context),
    ).json()

    project["members"] = [{"username": "testuser", "role": "write"}]
    denied = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources/{created['resource_id']}/rotate",
        headers=auth_headers,
        json=_resource_body(game_api_context, handle="opaque-api-rotated", path="game"),
    )
    assert denied.status_code == 403
    assert error_code(denied) == "project_no_access"

    project["members"] = [{"username": "testuser", "role": "admin"}]
    rotated = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources/{created['resource_id']}/rotate",
        headers=auth_headers,
        json=_resource_body(game_api_context, handle="opaque-api-rotated", path="game"),
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["generation"] == created["generation"] + 1
    assert rotated.json()["status"] == "pending"


def test_binding_api_rejects_traversal_and_client_supplied_status(
    client,
    auth_headers,
    game_api_context,
) -> None:
    game_api_context["project"]["members"] = [{"username": "testuser", "role": "admin"}]
    traversal = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
        json=_resource_body(game_api_context, path="../escape"),
    )
    assert traversal.status_code == 400
    assert error_code(traversal) == "game_resource_invalid"

    supplied_status = _resource_body(game_api_context)
    supplied_status["status"] = "ready"
    rejected = client.post(
        f"/api/compute/projects/{game_api_context['project_id']}/game-resources",
        headers=auth_headers,
        json=supplied_status,
    )
    assert rejected.status_code == 422
