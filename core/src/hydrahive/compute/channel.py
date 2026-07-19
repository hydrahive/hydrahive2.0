"""Authenticated, replay-safe read-only agent protocol handling."""

from __future__ import annotations

import hmac
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

from hydrahive.compute import audit, identity, job_protocol
from hydrahive.compute._node_codec import dump_json, normalize_certificate_fingerprint
from hydrahive.compute.channel_message import AgentMessage, ProtocolError, parse_message
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db
from hydrahive.settings import settings

NONCE_TTL_MINUTES = 10
CONNECTED_STATUSES = {"online", "degraded", "offline", "draining"}


def proxy_certificate_fingerprint(escaped_certificate: str) -> str:
    if not escaped_certificate or len(escaped_certificate) > 20_000:
        raise ProtocolError("agent_identity_invalid")
    try:
        certificate_pem = unquote(escaped_certificate).encode("ascii")
        return identity.certificate_fingerprint(certificate_pem)
    except (UnicodeError, identity.IdentityError) as exc:
        raise ProtocolError("agent_identity_invalid") from exc


def authenticate_node(node_id: str, escaped_certificate: str, proxy_secret: str) -> None:
    expected_proxy_secret = settings.compute_proxy_secret
    if not expected_proxy_secret or not hmac.compare_digest(proxy_secret, expected_proxy_secret):
        raise ProtocolError("agent_identity_invalid")
    normalized = normalize_certificate_fingerprint(proxy_certificate_fingerprint(escaped_certificate))
    with db() as conn:
        row = conn.execute(
            "SELECT certificate_fingerprint, status FROM compute_nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
    if (
        row is None
        or row["status"] not in CONNECTED_STATUSES
        or row["certificate_fingerprint"] is None
        or normalized is None
        or not hmac.compare_digest(row["certificate_fingerprint"], normalized)
    ):
        raise ProtocolError("agent_identity_invalid")


def _json_object(value: dict, field_name: str) -> str:
    try:
        return dump_json(value, field_name)
    except ValueError as exc:
        raise ProtocolError("agent_payload_invalid") from exc


def _health_errors(payload: dict[str, object]) -> list[str]:
    value = payload.get("health_errors", [])
    if not isinstance(value, list) or len(value) > 32:
        raise ProtocolError("agent_payload_invalid")
    errors = [item for item in value if isinstance(item, str) and 0 < len(item) <= 256]
    if len(errors) != len(value):
        raise ProtocolError("agent_payload_invalid")
    return errors


def accept_message(authenticated_node_id: str, message: AgentMessage) -> dict:
    if message.node_id != authenticated_node_id:
        raise ProtocolError("agent_node_mismatch")
    now = now_iso()
    nonce_expiry = (datetime.now(UTC) + timedelta(minutes=NONCE_TTL_MINUTES)).isoformat().replace("+00:00", "Z")
    with db(immediate=True) as conn:
        conn.execute("DELETE FROM compute_agent_nonces WHERE expires_at <= ?", (now,))
        node = conn.execute(
            "SELECT status, last_sequence FROM compute_nodes WHERE node_id = ?",
            (authenticated_node_id,),
        ).fetchone()
        if node is None or node["status"] not in CONNECTED_STATUSES:
            raise ProtocolError("agent_identity_invalid")
        if message.sequence <= node["last_sequence"]:
            raise ProtocolError("agent_sequence_replayed")
        try:
            conn.execute(
                "INSERT INTO compute_agent_nonces (node_id, nonce, expires_at) VALUES (?, ?, ?)",
                (authenticated_node_id, message.nonce, nonce_expiry),
            )
        except sqlite3.IntegrityError as exc:
            raise ProtocolError("agent_nonce_replayed") from exc

        updates = ["last_sequence = ?", "last_seen_at = ?", "updated_at = ?"]
        values: list[object] = [message.sequence, now, now]
        if message.type == "hello":
            agent_version = message.payload.get("agent_version")
            if not isinstance(agent_version, str) or not 0 < len(agent_version) <= 64:
                raise ProtocolError("agent_payload_invalid")
            updates.append("agent_version = ?")
            values.append(agent_version)
            audit.record_in_connection(
                conn,
                actor=f"node:{authenticated_node_id}",
                action="node.connected",
                node_id=authenticated_node_id,
                details={"sequence": message.sequence},
            )
        elif message.type == "capabilities":
            capabilities = message.payload.get("capabilities")
            resources = message.payload.get("resources")
            if not isinstance(capabilities, dict) or not isinstance(resources, dict):
                raise ProtocolError("agent_payload_invalid")
            updates.extend(("capabilities_json = ?", "resources_json = ?"))
            values.extend((_json_object(capabilities, "capabilities"), _json_object(resources, "resources")))
        elif message.type == "heartbeat":
            capabilities = message.payload.get("capabilities")
            resources = message.payload.get("resources")
            if not isinstance(capabilities, dict) or not isinstance(resources, dict):
                raise ProtocolError("agent_payload_invalid")
            errors = _health_errors(message.payload)
            status = "draining" if node["status"] == "draining" else ("degraded" if errors else "online")
            if status != node["status"]:
                audit.record_in_connection(
                    conn,
                    actor=f"node:{authenticated_node_id}",
                    action=f"node.{status}",
                    node_id=authenticated_node_id,
                    details={"from": node["status"], "reason": "heartbeat"},
                )
            updates.extend(
                (
                    "capabilities_json = ?",
                    "resources_json = ?",
                    "health_errors_json = ?",
                    "status = ?",
                )
            )
            values.extend(
                (
                    _json_object(capabilities, "capabilities"),
                    _json_object(resources, "resources"),
                    json.dumps(errors, separators=(",", ":")),
                    status,
                )
            )
        values.append(authenticated_node_id)
        conn.execute(
            f"UPDATE compute_nodes SET {', '.join(updates)} WHERE node_id = ?",
            values,
        )
    return {"type": "ack", "sequence": message.sequence, "accepted_at": now}


def response_for_message(authenticated_node_id: str, message: AgentMessage) -> dict:
    acknowledgement = accept_message(authenticated_node_id, message)
    if message.type in job_protocol.JOB_MESSAGE_TYPES:
        try:
            response = job_protocol.handle_message(authenticated_node_id, message.type, message.payload)
        except job_protocol.JobProtocolError as exc:
            raise ProtocolError("agent_job_invalid") from exc
        response["sequence"] = message.sequence
        return response
    if message.type == "hello":
        from hydrahive.compute import job_signing

        acknowledgement["job_signing_public_key"] = job_signing.public_key_text()
    return acknowledgement
