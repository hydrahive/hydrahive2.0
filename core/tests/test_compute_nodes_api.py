from __future__ import annotations

import sqlite3

import pytest

from hydrahive.compute import audit
from hydrahive.db.connection import db
from tests.conftest import error_code


def test_compute_nodes_require_admin(client, auth_headers, admin_headers) -> None:
    assert client.get("/api/compute/nodes").status_code == 401

    denied = client.get("/api/compute/nodes", headers=auth_headers)
    assert denied.status_code == 403
    assert error_code(denied) == "admin_only"

    allowed = client.get("/api/compute/nodes", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()[0]["node_id"] == "local"


def test_compute_admin_uses_current_role(client, admin_headers, monkeypatch) -> None:
    from hydrahive.api.middleware import users

    monkeypatch.setattr(
        users,
        "get_by_id",
        lambda user_id: {"user_id": user_id, "username": "admin", "role": "user"},
    )

    denied = client.get("/api/compute/nodes", headers=admin_headers)
    assert denied.status_code == 403
    assert error_code(denied) == "admin_only"


def test_enrollment_token_creation_requires_admin_and_is_audited(client, auth_headers, admin_headers) -> None:
    denied = client.post(
        "/api/compute/enrollments",
        headers=auth_headers,
        json={"requested_name": "API Auth Node"},
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/compute/enrollments",
        headers=admin_headers,
        json={"requested_name": "API Auth Node", "ttl_seconds": 300},
    )
    assert created.status_code == 201
    body = created.json()
    assert len(body["token"]) >= 43
    assert body["requested_name"] == "API Auth Node"

    records = audit.list_records(limit=10)
    record = next(item for item in records if item["action"] == "enrollment.created")
    assert record["actor"]
    assert record["actor"] != "admin"
    assert record["details"]["token_id"] == body["token_id"]
    assert "token" not in record["details"]

    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with db() as conn:
            conn.execute(
                "UPDATE compute_audit_log SET action = 'tampered' WHERE audit_id = ?",
                (record["audit_id"],),
            )
