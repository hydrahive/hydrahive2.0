from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import job_protocol, job_signing, jobs
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def protocol_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "protocol-jobs.db", raising=False)
    monkeypatch.setattr(settings, "compute_pki_dir", tmp_path / "pki", raising=False)
    init_db()
    node = node_db.create_node(
        node_id="node-protocol",
        name="Protocol Node",
        certificate_fingerprint="ab" * 32,
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    return node.node_id


def _job(node_id: str):
    return jobs.create_job(
        node_id=node_id,
        resource_kind="container",
        resource_id="demo",
        operation="container.start",
        generation=2,
        payload={"name": "demo"},
        idempotency_key="container:demo:start:2",
        created_by="admin",
    )


def test_job_poll_returns_signed_node_bound_offer(protocol_node: str) -> None:
    created = _job(protocol_node)
    response = job_protocol.handle_message(protocol_node, "job_poll", {})

    assert response["type"] == "job_offer"
    assert response["job"]["job_id"] == created.job_id
    assert response["job"]["node_id"] == protocol_node
    assert job_signing.verify_offer(response["job"], response["signature"], job_signing.public_key_text())

    tampered = dict(response["job"], operation="container.delete")
    assert not job_signing.verify_offer(tampered, response["signature"], job_signing.public_key_text())


def test_job_events_require_matching_node_job_and_lease(protocol_node: str) -> None:
    created = _job(protocol_node)
    offer = job_protocol.handle_message(protocol_node, "job_poll", {})
    lease_id = offer["job"]["lease_id"]

    started = job_protocol.handle_message(
        protocol_node,
        "job_started",
        {"job_id": created.job_id, "lease_id": lease_id},
    )
    assert started["type"] == "ack"
    assert jobs.get_job(created.job_id).status == "running"

    with pytest.raises(job_protocol.JobProtocolError, match="node"):
        job_protocol.handle_message(
            "different-node",
            "job_succeeded",
            {"job_id": created.job_id, "lease_id": lease_id, "result": {}},
        )

    job_protocol.handle_message(
        protocol_node,
        "job_succeeded",
        {"job_id": created.job_id, "lease_id": lease_id, "result": {"actual_state": "running"}},
    )
    assert jobs.get_job(created.job_id).status == "succeeded"
    rejected = job_protocol.handle_message(
        protocol_node,
        "job_failed",
        {
            "job_id": created.job_id,
            "lease_id": "stale-lease",
            "error_code": "late",
            "error_params": {},
        },
    )
    assert rejected == {"type": "job_rejected", "reason": "state_conflict"}


def test_job_poll_without_work_is_explicit(protocol_node: str) -> None:
    assert job_protocol.handle_message(protocol_node, "job_poll", {}) == {"type": "no_job"}
