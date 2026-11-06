"""Administrative isolation-approval persistence for Game Studio."""

from __future__ import annotations

import sqlite3

from hydrahive.compute import audit
from hydrahive.compute._game_resource_common import (
    MAX_DIGEST,
    MAX_VERSION,
    GameResourceError,
    approval_from_row,
    required,
)
from hydrahive.compute.models import GameIsolationApproval
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def get_isolation_approval(approval_id: str) -> GameIsolationApproval | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM compute_game_isolation_approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
    return approval_from_row(row) if row else None


def list_isolation_approvals(*, node_id: str | None = None) -> list[GameIsolationApproval]:
    with db() as conn:
        if node_id is None:
            rows = conn.execute(
                """SELECT * FROM compute_game_isolation_approvals
                   ORDER BY approved_at DESC, approval_id DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM compute_game_isolation_approvals WHERE node_id = ?
                   ORDER BY approved_at DESC, approval_id DESC""",
                (node_id,),
            ).fetchall()
    return [approval_from_row(row) for row in rows]


def active_approval(
    conn: sqlite3.Connection,
    *,
    approval_id: str,
    node_id: str,
    isolation_profile_id: str,
    runner_version: str,
    policy_digest: str,
) -> sqlite3.Row:
    row = conn.execute(
        """SELECT * FROM compute_game_isolation_approvals
           WHERE approval_id = ? AND node_id = ? AND isolation_profile_id = ?
             AND runner_version = ? AND policy_digest = ? AND status = 'active'""",
        (approval_id, node_id, isolation_profile_id, runner_version, policy_digest),
    ).fetchone()
    if row is None:
        raise GameResourceError("game_isolation_approval_invalid")
    return row


def approve_isolation(
    *,
    node_id: str,
    isolation_profile_id: str,
    runner_version: str,
    policy_digest: str,
    proof_digest: str,
    approved_by: str,
) -> GameIsolationApproval:
    node_id = required(node_id, "node_id")
    isolation_profile_id = required(isolation_profile_id, "isolation_profile_id")
    runner_version = required(runner_version, "runner_version", maximum=MAX_VERSION)
    policy_digest = required(policy_digest, "policy_digest", maximum=MAX_DIGEST)
    proof_digest = required(proof_digest, "proof_digest", maximum=MAX_DIGEST)
    approved_by = required(approved_by, "approved_by")
    approval_id = uuid7()
    timestamp = now_iso()
    with db(immediate=True) as conn:
        node = conn.execute(
            "SELECT kind, status, approved_at FROM compute_nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if node is None:
            raise GameResourceError("compute_node_not_found")
        if node["kind"] != "agent" or node["approved_at"] is None or node["status"] in {"pending", "revoked"}:
            raise GameResourceError("game_isolation_node_not_approved")
        conn.execute(
            """INSERT INTO compute_game_isolation_approvals
                   (approval_id, node_id, isolation_profile_id, runner_version,
                    policy_digest, proof_digest, status, approved_by, approved_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (
                approval_id,
                node_id,
                isolation_profile_id,
                runner_version,
                policy_digest,
                proof_digest,
                approved_by,
                timestamp,
            ),
        )
        audit.record_in_connection(
            conn,
            actor=approved_by,
            action="game.isolation_approval.approved",
            node_id=node_id,
            details={
                "approval_id": approval_id,
                "isolation_profile_id": isolation_profile_id,
                "runner_version": runner_version,
                "policy_digest": policy_digest,
                "proof_digest": proof_digest,
            },
        )
    approval = get_isolation_approval(approval_id)
    if approval is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("created isolation approval could not be read back")
    return approval
