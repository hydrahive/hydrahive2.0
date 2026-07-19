from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import channel, jobs
from hydrahive.compute import db as node_db
from hydrahive.compute.channel_message import ProtocolError, parse_message
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def two_nodes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "hardening.db", raising=False)
    init_db()
    ids = []
    for name in ("node-a", "node-b"):
        node = node_db.create_node(
            node_id=name,
            name=name,
            certificate_fingerprint=(("aa" if name == "node-a" else "bb") * 32),
            capabilities={"incus": True, "instance_types": ["container"]},
        )
        node_db.approve_node(node.node_id, "admin")
        node_db.transition_node_status(node.node_id, "online")
        ids.append(node.node_id)
    return ids[0], ids[1]


def _queue_job(node_id: str) -> str:
    job = jobs.create_job(
        node_id=node_id,
        resource_kind="container",
        resource_id="019f7be0-95fb-73d3-a87a-2290c85ea427",
        operation="container.inspect",
        generation=0,
        payload={"name": "demo"},
        idempotency_key=f"iso-{node_id}",
        created_by="admin-id",
    )
    return job.job_id


def test_node_can_only_claim_its_own_jobs(two_nodes) -> None:
    node_a, node_b = two_nodes
    _queue_job(node_a)

    # node-b must not be able to claim node-a's job.
    assert jobs.claim_next_job(node_b) is None
    claimed = jobs.claim_next_job(node_a)
    assert claimed is not None and claimed.node_id == node_a


def test_node_cannot_read_foreign_job_via_protocol(two_nodes) -> None:
    node_a, node_b = two_nodes
    job_id = _queue_job(node_a)
    claimed = jobs.claim_next_job(node_a)
    assert claimed is not None and claimed.lease_id is not None

    from hydrahive.compute import job_protocol

    # node-b claims ownership of node-a's job → rejected as not belonging to it.
    with pytest.raises(job_protocol.JobProtocolError):
        job_protocol.handle_message(
            node_b,
            "job_started",
            {"job_id": job_id, "lease_id": claimed.lease_id},
        )


def test_revoked_node_cannot_authenticate(two_nodes, monkeypatch) -> None:
    node_a, _ = two_nodes
    node_db.revoke_node(node_a, actor="admin-id")

    monkeypatch.setattr(settings, "compute_proxy_secret", "proxy-secret", raising=False)
    monkeypatch.setattr(channel, "proxy_certificate_fingerprint", lambda cert: "aa" * 32)

    with pytest.raises(ProtocolError, match="agent_identity_invalid"):
        channel.authenticate_node(node_a, "cert-pem", "proxy-secret")


def test_revoked_node_message_is_rejected(two_nodes) -> None:
    import json
    from datetime import UTC, datetime

    node_a, _ = two_nodes
    node_db.revoke_node(node_a, actor="admin-id")

    message = parse_message(
        json.dumps(
            {
                "type": "heartbeat",
                "protocol_version": 1,
                "node_id": node_a,
                "sequence": 5,
                "nonce": "nonce-value-123456",
                "sent_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "payload": {"capabilities": {}, "resources": {}, "health_errors": []},
            }
        )
    )
    with pytest.raises(ProtocolError, match="agent_identity_invalid"):
        channel.accept_message(node_a, message)
