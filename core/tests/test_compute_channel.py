from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hydrahive.compute import channel, channel_monitor
from hydrahive.compute import db as node_db
from hydrahive.db.connection import db, init_db
from hydrahive.settings import settings


@pytest.fixture
def connected_node(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "channel.db", raising=False)
    monkeypatch.setattr(settings, "compute_proxy_secret", "proxy-secret", raising=False)
    monkeypatch.setattr(
        channel,
        "proxy_certificate_fingerprint",
        lambda certificate: "00" * 32 if certificate == "wrong-cert" else "ab" * 32,
    )
    init_db()
    node = node_db.create_node(
        node_id="node-channel",
        name="Channel Node",
        certificate_fingerprint="ab" * 32,
    )
    node_db.approve_node(node.node_id, "admin-id")
    return node.node_id


def _raw(node_id: str, *, sequence: int, nonce: str, kind: str = "heartbeat", payload=None) -> str:
    return json.dumps(
        {
            "type": kind,
            "protocol_version": 1,
            "node_id": node_id,
            "sequence": sequence,
            "nonce": nonce,
            "sent_at": datetime.now(UTC).isoformat(),
            "payload": (payload if payload is not None else {"capabilities": {}, "resources": {}, "health_errors": []}),
        }
    )


def test_agent_identity_requires_proxy_secret_fingerprint_and_online_status(connected_node: str) -> None:
    channel.authenticate_node(connected_node, "valid-cert", "proxy-secret")

    for certificate, secret in (("wrong-cert", "proxy-secret"), ("valid-cert", "wrong")):
        with pytest.raises(channel.ProtocolError, match="agent_identity_invalid"):
            channel.authenticate_node(connected_node, certificate, secret)

    node_db.revoke_node(connected_node, actor="admin-id")
    with pytest.raises(channel.ProtocolError, match="agent_identity_invalid"):
        channel.authenticate_node(connected_node, "valid-cert", "proxy-secret")


def test_protocol_rejects_replayed_sequence_nonce_and_wrong_node(connected_node: str) -> None:
    first = channel.parse_message(_raw(connected_node, sequence=1, nonce="nonce-0000000001"))
    assert channel.accept_message(connected_node, first)["sequence"] == 1

    with pytest.raises(channel.ProtocolError, match="sequence_replayed"):
        channel.accept_message(connected_node, first)

    repeated_nonce = channel.parse_message(_raw(connected_node, sequence=2, nonce="nonce-0000000001"))
    with pytest.raises(channel.ProtocolError, match="nonce_replayed"):
        channel.accept_message(connected_node, repeated_nonce)

    wrong_node = channel.parse_message(_raw("other-node", sequence=2, nonce="nonce-0000000002"))
    with pytest.raises(channel.ProtocolError, match="node_mismatch"):
        channel.accept_message(connected_node, wrong_node)


def test_protocol_validates_timestamp_schema_and_payload(connected_node: str) -> None:
    stale = json.loads(_raw(connected_node, sequence=1, nonce="nonce-0000000001"))
    stale["sent_at"] = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    with pytest.raises(channel.ProtocolError, match="timestamp_invalid"):
        channel.parse_message(json.dumps(stale))

    invalid = json.loads(_raw(connected_node, sequence=1, nonce="nonce-0000000002"))
    invalid["unexpected"] = True
    with pytest.raises(channel.ProtocolError, match="message_invalid"):
        channel.parse_message(json.dumps(invalid))

    bad_payload = channel.parse_message(
        _raw(connected_node, sequence=1, nonce="nonce-0000000003", payload={"resources": [], "health_errors": []})
    )
    with pytest.raises(channel.ProtocolError, match="payload_invalid"):
        channel.accept_message(connected_node, bad_payload)


def test_capabilities_and_heartbeats_update_node_health(connected_node: str) -> None:
    hello = channel.parse_message(
        _raw(
            connected_node,
            sequence=1,
            nonce="nonce-0000000001",
            kind="hello",
            payload={"agent_version": "0.1.0"},
        )
    )
    channel.accept_message(connected_node, hello)
    capabilities = channel.parse_message(
        _raw(
            connected_node,
            sequence=2,
            nonce="nonce-0000000002",
            kind="capabilities",
            payload={"capabilities": {"kvm": True}, "resources": {"cpu_cores": 8}},
        )
    )
    channel.accept_message(connected_node, capabilities)
    degraded = channel.parse_message(
        _raw(
            connected_node,
            sequence=3,
            nonce="nonce-0000000003",
            payload={
                "capabilities": {"kvm": False},
                "resources": {"cpu_load_1m": 1.5},
                "health_errors": ["incus_unavailable"],
            },
        )
    )
    channel.accept_message(connected_node, degraded)

    node = node_db.get_node(connected_node)
    assert node.agent_version == "0.1.0"
    assert node.capabilities == {"kvm": False}
    assert node.resources == {"cpu_load_1m": 1.5}
    assert node.health_errors == ["incus_unavailable"]
    assert node.status == "degraded"
    assert node.last_sequence == 3
    assert node.last_seen_at is not None
    with db() as conn:
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM compute_audit_log WHERE node_id = ? ORDER BY created_at, audit_id",
                (connected_node,),
            )
        ]
    assert "node.degraded" in actions


def test_websocket_channel_requires_bound_identity_and_acknowledges(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "compute_proxy_secret", "proxy-secret", raising=False)
    monkeypatch.setattr(channel, "proxy_certificate_fingerprint", lambda certificate: "cd" * 32)
    node = node_db.create_node(
        node_id="node-websocket",
        name="WebSocket Node",
        certificate_fingerprint="cd" * 32,
    )
    node_db.approve_node(node.node_id, "admin-id")
    headers = {
        "x-hydrahive-node-id": node.node_id,
        "x-hydrahive-client-cert": "valid-cert",
        "x-hydrahive-proxy-secret": "proxy-secret",
    }
    with client.websocket_connect("/api/compute/agent/connect", headers=headers) as websocket:
        websocket.send_text(_raw(node.node_id, sequence=1, nonce="nonce-websocket01"))
        assert websocket.receive_json()["sequence"] == 1


def test_dead_detection_marks_degraded_then_offline(connected_node: str) -> None:
    node_db.transition_node_status(connected_node, "online")
    old = (datetime.now(UTC) - timedelta(seconds=60)).isoformat().replace("+00:00", "Z")
    with db() as conn:
        conn.execute("UPDATE compute_nodes SET last_seen_at = ? WHERE node_id = ?", (old, connected_node))
    assert channel_monitor.mark_stale_nodes(degraded_after=45, offline_after=90) == (1, 0)
    assert node_db.get_node(connected_node).status == "degraded"

    older = (datetime.now(UTC) - timedelta(seconds=120)).isoformat().replace("+00:00", "Z")
    with db() as conn:
        conn.execute("UPDATE compute_nodes SET last_seen_at = ? WHERE node_id = ?", (older, connected_node))
    assert channel_monitor.mark_stale_nodes(degraded_after=45, offline_after=90) == (0, 1)
    assert node_db.get_node(connected_node).status == "offline"
    with db() as conn:
        monitor_actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM compute_audit_log WHERE actor = 'system:compute-monitor' ORDER BY created_at"
            )
        ]
    assert monitor_actions == ["node.degraded", "node.offline"]
