"""Parameterized persistence operations for the compute-node registry."""

from __future__ import annotations

from hydrahive.compute._node_codec import (
    ALLOWED_STATUS_TRANSITIONS,
    dump_json,
    row_to_node,
    validate_identity,
    validate_kind,
    validate_status,
)
from hydrahive.compute.models import ComputeNode, JSONObject, NodeKind, NodeStatus
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

LOCAL_NODE_ID = "local"


def create_node(
    *,
    node_id: str,
    name: str,
    kind: NodeKind = "agent",
    status: NodeStatus = "pending",
    certificate_fingerprint: str | None = None,
    protocol_version: int = 1,
    agent_version: str | None = None,
    capabilities: JSONObject | None = None,
    resources: JSONObject | None = None,
    labels: JSONObject | None = None,
) -> ComputeNode:
    validate_identity(node_id, name)
    validate_kind(kind)
    validate_status(status)
    if node_id == LOCAL_NODE_ID or kind == "local":
        raise ValueError("local node identity is reserved")
    if protocol_version < 1:
        raise ValueError("protocol_version must be at least 1")
    capabilities_json = dump_json(capabilities or {}, "capabilities")
    resources_json = dump_json(resources or {}, "resources")
    labels_json = dump_json(labels or {}, "labels")
    timestamp = now_iso()
    with db() as conn:
        conn.execute(
            """INSERT INTO compute_nodes (
                   node_id, name, kind, status, certificate_fingerprint,
                   protocol_version, agent_version, capabilities_json,
                   resources_json, labels_json, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node_id,
                name,
                kind,
                status,
                certificate_fingerprint,
                protocol_version,
                agent_version,
                capabilities_json,
                resources_json,
                labels_json,
                timestamp,
                timestamp,
            ),
        )
    node = get_node(node_id)
    if node is None:  # pragma: no cover - defensive invariant
        raise RuntimeError("created compute node could not be read back")
    return node


def get_node(node_id: str) -> ComputeNode | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
    return row_to_node(row) if row else None


def list_nodes() -> list[ComputeNode]:
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM compute_nodes
               ORDER BY CASE WHEN node_id = ? THEN 0 ELSE 1 END, name, node_id""",
            (LOCAL_NODE_ID,),
        ).fetchall()
    return [row_to_node(row) for row in rows]


def update_node(
    node_id: str,
    *,
    name: str | None = None,
    status: NodeStatus | None = None,
    certificate_fingerprint: str | None = None,
    protocol_version: int | None = None,
    agent_version: str | None = None,
    capabilities: JSONObject | None = None,
    resources: JSONObject | None = None,
    labels: JSONObject | None = None,
    last_seen_at: str | None = None,
    approved_at: str | None = None,
    approved_by: str | None = None,
) -> ComputeNode | None:
    current = get_node(node_id)
    if current is None:
        return None
    fields: list[str] = []
    values: list[object] = []
    if name is not None:
        validate_identity(node_id, name)
        fields.append("name = ?")
        values.append(name)
    if status is not None:
        validate_status(status)
        if status != current.status and status not in ALLOWED_STATUS_TRANSITIONS[current.status]:
            raise ValueError(f"invalid node status transition: {current.status} -> {status}")
        fields.append("status = ?")
        values.append(status)
    if certificate_fingerprint is not None:
        fields.append("certificate_fingerprint = ?")
        values.append(certificate_fingerprint)
    if protocol_version is not None:
        if protocol_version < 1:
            raise ValueError("protocol_version must be at least 1")
        fields.append("protocol_version = ?")
        values.append(protocol_version)
    for column, value in (
        ("agent_version", agent_version),
        ("last_seen_at", last_seen_at),
        ("approved_at", approved_at),
        ("approved_by", approved_by),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(value)
    for column, value, field_name in (
        ("capabilities_json", capabilities, "capabilities"),
        ("resources_json", resources, "resources"),
        ("labels_json", labels, "labels"),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(dump_json(value, field_name))
    if not fields:
        return current
    fields.append("updated_at = ?")
    values.extend((now_iso(), node_id))
    with db() as conn:
        conn.execute(
            f"UPDATE compute_nodes SET {', '.join(fields)} WHERE node_id = ?",
            values,
        )
    return get_node(node_id)


def revoke_node(node_id: str) -> ComputeNode | None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node cannot be revoked")
    current = get_node(node_id)
    if current is None:
        return None
    if current.status != "revoked" and "revoked" not in ALLOWED_STATUS_TRANSITIONS[current.status]:
        raise ValueError(f"invalid node status transition: {current.status} -> revoked")
    timestamp = now_iso()
    with db() as conn:
        conn.execute(
            """UPDATE compute_nodes
               SET status = ?, revoked_at = ?, updated_at = ?
               WHERE node_id = ?""",
            ("revoked", timestamp, timestamp, node_id),
        )
    return get_node(node_id)


def delete_node(node_id: str) -> None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node cannot be deleted")
    with db() as conn:
        conn.execute("DELETE FROM compute_nodes WHERE node_id = ?", (node_id,))
