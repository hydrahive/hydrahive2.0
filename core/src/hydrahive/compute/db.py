"""Parameterized persistence operations for the compute-node registry."""

from __future__ import annotations

from hydrahive.compute._node_codec import (
    dump_json,
    normalize_certificate_fingerprint,
    row_to_node,
    validate_identity,
    validate_kind,
    validate_status,
)
from hydrahive.compute._node_status import approve_node, revoke_node, transition_node_status
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
    if status != "pending":
        raise ValueError("new agent nodes must start in pending status")
    if node_id == LOCAL_NODE_ID or kind == "local":
        raise ValueError("local node identity is reserved")
    if protocol_version < 1:
        raise ValueError("protocol_version must be at least 1")
    certificate_fingerprint = normalize_certificate_fingerprint(certificate_fingerprint)
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
    protocol_version: int | None = None,
    agent_version: str | None = None,
    capabilities: JSONObject | None = None,
    resources: JSONObject | None = None,
    labels: JSONObject | None = None,
    last_seen_at: str | None = None,
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
    if protocol_version is not None:
        if protocol_version < 1:
            raise ValueError("protocol_version must be at least 1")
        fields.append("protocol_version = ?")
        values.append(protocol_version)
    for column, value in (
        ("agent_version", agent_version),
        ("last_seen_at", last_seen_at),
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


def delete_node(node_id: str) -> None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node cannot be deleted")
    with db(immediate=True) as conn:
        in_use = conn.execute(
            """SELECT
                   EXISTS(SELECT 1 FROM containers WHERE node_id = ?)
                   OR EXISTS(SELECT 1 FROM vms WHERE node_id = ?)
                   OR EXISTS(SELECT 1 FROM compute_jobs WHERE node_id = ?)""",
            (node_id, node_id, node_id),
        ).fetchone()[0]
        if in_use:
            raise ValueError("compute node is still in use")
        conn.execute("DELETE FROM compute_nodes WHERE node_id = ?", (node_id,))
