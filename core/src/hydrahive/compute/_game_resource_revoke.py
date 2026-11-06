"""Atomic approval and node-wide Game Studio invalidation."""

from __future__ import annotations

import sqlite3

from hydrahive.compute import audit
from hydrahive.compute._game_approvals import get_isolation_approval
from hydrahive.compute._game_resource_common import GameResourceError, approval_from_row, required
from hydrahive.compute.models import GameIsolationApproval
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db


def revoke_isolation_approval(approval_id: str, *, revoked_by: str) -> GameIsolationApproval:
    approval_id = required(approval_id, "approval_id")
    revoked_by = required(revoked_by, "revoked_by")
    timestamp = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM compute_game_isolation_approvals WHERE approval_id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            raise GameResourceError("game_isolation_approval_not_found")
        current = approval_from_row(row)
        if current.status == "revoked":
            return current
        invalidated = conn.execute(
            """UPDATE compute_game_workspaces
               SET status = 'revoked', revoked_at = ?, updated_at = ?
               WHERE isolation_approval_id = ? AND status != 'revoked'""",
            (timestamp, timestamp, approval_id),
        ).rowcount
        conn.execute(
            """UPDATE compute_game_isolation_approvals
               SET status = 'revoked', revoked_by = ?, revoked_at = ?
               WHERE approval_id = ? AND status = 'active'""",
            (revoked_by, timestamp, approval_id),
        )
        audit.record_in_connection(
            conn,
            actor=revoked_by,
            action="game.isolation_approval.revoked",
            node_id=current.node_id,
            details={"approval_id": approval_id, "invalidated_resources": invalidated},
        )
    revoked = get_isolation_approval(approval_id)
    if revoked is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("revoked isolation approval could not be read back")
    return revoked


def revoke_for_node_in_connection(
    conn: sqlite3.Connection,
    *,
    node_id: str,
    actor: str | None,
    timestamp: str,
) -> tuple[int, int]:
    """Invalidate dependent resources during the surrounding atomic node revoke."""
    invalidated_resources = conn.execute(
        """UPDATE compute_game_workspaces
           SET status = 'revoked', revoked_at = ?, updated_at = ?
           WHERE node_id = ? AND status != 'revoked'""",
        (timestamp, timestamp, node_id),
    ).rowcount
    invalidated_approvals = conn.execute(
        """UPDATE compute_game_isolation_approvals
           SET status = 'revoked', revoked_by = ?, revoked_at = ?
           WHERE node_id = ? AND status = 'active'""",
        (actor or "system:node-revoke", timestamp, node_id),
    ).rowcount
    if actor is not None and (invalidated_resources or invalidated_approvals):
        audit.record_in_connection(
            conn,
            actor=actor,
            action="game.node_bindings.revoked",
            node_id=node_id,
            details={
                "invalidated_resources": invalidated_resources,
                "invalidated_approvals": invalidated_approvals,
            },
        )
    return invalidated_resources, invalidated_approvals
