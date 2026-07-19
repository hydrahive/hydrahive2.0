"""Atomic trust and health-state transitions for compute nodes."""

from __future__ import annotations

from hydrahive.compute import audit
from hydrahive.compute._node_codec import ALLOWED_STATUS_TRANSITIONS, row_to_node, validate_status
from hydrahive.compute.models import ComputeNode, NodeStatus
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db

LOCAL_NODE_ID = "local"


def _read_node(node_id: str) -> ComputeNode | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
    return row_to_node(row) if row else None


def approve_node(node_id: str, approved_by: str) -> ComputeNode | None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node does not require approval")
    if not approved_by or len(approved_by) > 128:
        raise ValueError("approved_by must contain 1-128 characters")
    timestamp = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            return None
        current = row_to_node(row)
        if current.status != "pending":
            raise ValueError("only pending nodes can be approved")
        if current.certificate_fingerprint is None:
            raise ValueError("node requires a certificate fingerprint before approval")
        conn.execute(
            """UPDATE compute_nodes
               SET status = 'offline', approved_at = ?, approved_by = ?, updated_at = ?
               WHERE node_id = ? AND status = 'pending'""",
            (timestamp, approved_by, timestamp, node_id),
        )
        audit.record_in_connection(
            conn,
            actor=approved_by,
            action="node.approved",
            node_id=node_id,
        )
    return _read_node(node_id)


def transition_node_status(
    node_id: str,
    status: NodeStatus,
    *,
    actor: str | None = None,
) -> ComputeNode | None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node status is managed by the control plane")
    validate_status(status)
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            return None
        current = row_to_node(row)
        if status == current.status:
            return current
        if status not in ALLOWED_STATUS_TRANSITIONS[current.status]:
            raise ValueError(f"invalid node status transition: {current.status} -> {status}")
        if status == "online" and (
            current.certificate_fingerprint is None or current.approved_at is None or current.approved_by is None
        ):
            raise ValueError("node must be activated through approval before going online")
        result = conn.execute(
            """UPDATE compute_nodes SET status = ?, updated_at = ?
               WHERE node_id = ? AND status = ?""",
            (status, now_iso(), node_id, current.status),
        )
        if result.rowcount != 1:  # pragma: no cover - protected by BEGIN IMMEDIATE
            raise RuntimeError("compute node status changed concurrently")
        if actor is not None:
            audit.record_in_connection(
                conn,
                actor=actor,
                action=f"node.{status}",
                node_id=node_id,
            )
    return _read_node(node_id)


def revoke_node(node_id: str, *, actor: str | None = None) -> ComputeNode | None:
    if node_id == LOCAL_NODE_ID:
        raise ValueError("local node cannot be revoked")
    timestamp = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            return None
        current = row_to_node(row)
        if current.status != "revoked" and "revoked" not in ALLOWED_STATUS_TRANSITIONS[current.status]:
            raise ValueError(f"invalid node status transition: {current.status} -> revoked")
        conn.execute(
            """UPDATE compute_nodes
               SET status = ?, revoked_at = COALESCE(revoked_at, ?), updated_at = ?
               WHERE node_id = ? AND status = ?""",
            ("revoked", timestamp, timestamp, node_id, current.status),
        )
        if actor is not None:
            audit.record_in_connection(
                conn,
                actor=actor,
                action="node.revoked",
                node_id=node_id,
            )
    return _read_node(node_id)
