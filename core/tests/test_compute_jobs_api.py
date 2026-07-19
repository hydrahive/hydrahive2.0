from __future__ import annotations

import pytest

from hydrahive.api.middleware import users
from hydrahive.compute import db as node_db
from hydrahive.compute import jobs
from tests.conftest import error_code


@pytest.fixture
def api_jobs() -> dict[str, object]:
    node_id = "node-jobs-api"
    if node_db.get_node(node_id) is None:
        node_db.create_node(
            node_id=node_id,
            name="Jobs API Node",
            certificate_fingerprint="ef" * 32,
        )
        node_db.approve_node(node_id, "admin")
        node_db.transition_node_status(node_id, "online")
    user_id = users.get_by_username("testuser")["user_id"]
    admin_id = users.get_by_username("admin")["user_id"]
    user_job = jobs.create_job(
        node_id=node_id,
        resource_kind="container",
        resource_id="user-demo",
        operation="container.start",
        generation=1,
        payload={"secret": "must-not-be-returned"},
        idempotency_key="api-user-job",
        created_by=user_id,
    )
    admin_job = jobs.create_job(
        node_id=node_id,
        resource_kind="container",
        resource_id="admin-demo",
        operation="container.stop",
        generation=1,
        payload={},
        idempotency_key="api-admin-job",
        created_by=admin_id,
    )
    return {"user": user_job, "admin": admin_job}


def test_job_list_requires_auth_scopes_owner_and_never_returns_payload(
    client, auth_headers, admin_headers, api_jobs
) -> None:
    assert client.get("/api/compute/jobs").status_code == 401

    owned = client.get("/api/compute/jobs", headers=auth_headers)
    assert owned.status_code == 200
    assert [item["job_id"] for item in owned.json()] == [api_jobs["user"].job_id]
    assert "payload" not in owned.json()[0]
    assert "idempotency_key" not in owned.json()[0]

    admin = client.get("/api/compute/jobs", headers=admin_headers)
    assert admin.status_code == 200
    ids = {item["job_id"] for item in admin.json()}
    assert {api_jobs["user"].job_id, api_jobs["admin"].job_id} <= ids


def test_job_detail_events_and_cancel_enforce_ownership(client, auth_headers, admin_headers, api_jobs) -> None:
    admin_job_id = api_jobs["admin"].job_id
    hidden = client.get(f"/api/compute/jobs/{admin_job_id}", headers=auth_headers)
    assert hidden.status_code == 404
    assert error_code(hidden) == "compute_job_not_found"

    user_job_id = api_jobs["user"].job_id
    detail = client.get(f"/api/compute/jobs/{user_job_id}", headers=auth_headers)
    assert detail.status_code == 200
    events = client.get(f"/api/compute/jobs/{user_job_id}/events", headers=auth_headers)
    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "queued"

    cancelled = client.post(f"/api/compute/jobs/{user_job_id}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    repeated = client.post(f"/api/compute/jobs/{user_job_id}/cancel", headers=auth_headers)
    assert repeated.status_code == 409
    assert error_code(repeated) == "compute_job_transition_invalid"

    assert client.get(f"/api/compute/jobs/{admin_job_id}", headers=admin_headers).status_code == 200
