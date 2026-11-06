from __future__ import annotations

import hashlib

import pytest

from hydrahive.api.middleware import users
from hydrahive.compute import db as node_db
from hydrahive.compute import game_resources
from hydrahive.db._utils import uuid7
from hydrahive.projects import config as project_config
from tests.conftest import error_code

DIGEST = "sha256:" + "b" * 64


@pytest.fixture
def game_jobs_api_context(client, admin_headers, monkeypatch) -> dict:
    node_id = f"game-jobs-api-{uuid7()}"
    node_db.create_node(
        node_id=node_id,
        name=f"Game Jobs API {uuid7()}",
        certificate_fingerprint=hashlib.sha256(node_id.encode()).hexdigest(),
    )
    node_db.approve_node(node_id, users.get_by_username("admin")["user_id"])
    node_db.transition_node_status(node_id, "online")
    approval = client.post(
        "/api/compute/game-isolation-approvals",
        headers=admin_headers,
        json={
            "node_id": node_id,
            "isolation_profile_id": "linux-microvm-v1",
            "runner_version": "1.0.0",
            "policy_digest": "sha256:policy-api",
            "proof_digest": "sha256:proof-api",
        },
    ).json()
    project_a = {"id": f"project-{uuid7()}", "created_by": "other", "status": "active", "members": []}
    project_b = {"id": f"project-{uuid7()}", "created_by": "other", "status": "active", "members": []}
    projects = {project_a["id"]: project_a, project_b["id"]: project_b}
    monkeypatch.setattr(project_config, "get", projects.get)
    project_a["members"] = [{"username": "testuser", "role": "admin"}]
    return {
        "node_id": node_id,
        "approval": approval,
        "project_a": project_a,
        "project_b": project_b,
    }


def _resource_body(context: dict) -> dict:
    approval = context["approval"]
    return {
        "node_id": context["node_id"],
        "workspace_handle": "opaque-api-workspace",
        "engine": "godot",
        "engine_version": "4.5.1",
        "engine_project_relpath": ".",
        "trust_mode": "sandboxed",
        "isolation_approval_id": approval["approval_id"],
        "isolation_profile_id": approval["isolation_profile_id"],
        "runner_version": approval["runner_version"],
        "policy_digest": approval["policy_digest"],
    }


def _job_body(resource_id: str, *, key: str) -> dict:
    return {
        "game_resource_id": resource_id,
        "operation": "game.project.validate",
        "source_commit_sha": "a" * 40,
        "source_snapshot_digest": None,
        "inventory_snapshot_id": "inventory-a",
        "engine": "godot",
        "engine_version": "4.5.1",
        "toolchain_digest": DIGEST,
        "profile_id": "debug-desktop",
        "input_revision": 1,
        "limits": {
            "timeout_seconds": 900,
            "cpu_cores": 4,
            "memory_mb": 8192,
            "disk_mb": 16384,
            "pids": 256,
            "network": "off",
        },
        "operation_payload": {"validation_profile_id": "validation-default"},
        "idempotency_key": key,
    }


@pytest.fixture
def ready_api_resource(client, auth_headers, game_jobs_api_context) -> dict:
    context = game_jobs_api_context
    context["project_a"]["members"] = [{"username": "testuser", "role": "admin"}]
    created = client.post(
        f"/api/compute/projects/{context['project_a']['id']}/game-resources",
        headers=auth_headers,
        json=_resource_body(context),
    )
    assert created.status_code == 201, created.text
    resource = created.json()
    game_resources.confirm_workspace(
        project_id=context["project_a"]["id"],
        resource_id=resource["resource_id"],
        authenticated_node_id=context["node_id"],
        workspace_handle=resource["workspace_handle"],
        workspace_generation=resource["generation"],
    )
    context["resource"] = resource
    return context


@pytest.mark.parametrize("project_role", [None, "read"])
def test_game_job_start_requires_project_write_role(
    client, auth_headers, ready_api_resource, project_role
) -> None:
    project = ready_api_resource["project_a"]
    project["members"] = [] if project_role is None else [{"username": "testuser", "role": project_role}]

    response = client.post(
        f"/api/compute/projects/{project['id']}/game-jobs",
        headers=auth_headers,
        json=_job_body(ready_api_resource["resource"]["resource_id"], key=f"denied-{project_role}"),
    )

    assert response.status_code == 403
    assert error_code(response) == "project_no_access"


def test_game_job_routes_use_project_roles_immutable_user_id_and_composite_scope(
    client, auth_headers, ready_api_resource
) -> None:
    context = ready_api_resource
    project_a = context["project_a"]
    project_a["members"] = [{"username": "testuser", "role": "write"}]
    created = client.post(
        f"/api/compute/projects/{project_a['id']}/game-jobs",
        headers=auth_headers,
        json=_job_body(context["resource"]["resource_id"], key="api-game-create"),
    )
    assert created.status_code == 201, created.text
    job = created.json()
    assert job["created_by"] == users.get_by_username("testuser")["user_id"]
    assert "payload" not in job

    project_a["members"] = [{"username": "testuser", "role": "read"}]
    assert client.get(
        f"/api/compute/projects/{project_a['id']}/game-jobs/{job['job_id']}", headers=auth_headers
    ).status_code == 200

    project_b = context["project_b"]
    project_b["members"] = [{"username": "testuser", "role": "read"}]
    cross_project = client.get(
        f"/api/compute/projects/{project_b['id']}/game-jobs/{job['job_id']}", headers=auth_headers
    )
    assert cross_project.status_code == 404
    assert error_code(cross_project) == "game_job_not_found"

    assert client.get(f"/api/compute/jobs/{job['job_id']}", headers=auth_headers).status_code == 404
    legacy_list = client.get("/api/compute/jobs", headers=auth_headers)
    assert legacy_list.status_code == 200
    assert all(item["job_id"] != job["job_id"] for item in legacy_list.json())


def test_game_job_cancel_requires_write_and_unknown_fields_are_rejected(
    client, auth_headers, ready_api_resource
) -> None:
    context = ready_api_resource
    project = context["project_a"]
    project["members"] = [{"username": "testuser", "role": "write"}]
    body = _job_body(context["resource"]["resource_id"], key="api-game-cancel")
    body["shell"] = "rm -rf /"
    rejected = client.post(
        f"/api/compute/projects/{project['id']}/game-jobs", headers=auth_headers, json=body
    )
    assert rejected.status_code == 422

    body.pop("shell")
    created = client.post(
        f"/api/compute/projects/{project['id']}/game-jobs", headers=auth_headers, json=body
    ).json()
    project["members"] = [{"username": "testuser", "role": "read"}]
    denied = client.post(
        f"/api/compute/projects/{project['id']}/game-jobs/{created['job_id']}/cancel",
        headers=auth_headers,
    )
    assert denied.status_code == 403
    assert error_code(denied) == "project_no_access"

    project["members"] = [{"username": "testuser", "role": "write"}]
    cancelled = client.post(
        f"/api/compute/projects/{project['id']}/game-jobs/{created['job_id']}/cancel",
        headers=auth_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
