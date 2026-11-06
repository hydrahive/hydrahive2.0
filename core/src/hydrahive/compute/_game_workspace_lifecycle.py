"""Authenticated confirmation and revocation of Game Studio workspaces."""

from __future__ import annotations

from hydrahive.compute import audit
from hydrahive.compute._game_approvals import active_approval
from hydrahive.compute._game_resource_common import (
    EXECUTABLE_NODE_STATUSES,
    GameResourceError,
    required,
    workspace_from_row,
    workspace_handle as validate_workspace_handle,
)
from hydrahive.compute._game_workspaces import get_workspace
from hydrahive.compute.models import ComputeGameWorkspace
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db


def confirm_workspace(
    *,
    project_id: str,
    resource_id: str,
    authenticated_node_id: str,
    workspace_handle: str,
    workspace_generation: int,
) -> ComputeGameWorkspace:
    """Internally confirm an exact handle after the caller authenticated the node."""
    project_id = required(project_id, "project_id")
    resource_id = required(resource_id, "resource_id")
    authenticated_node_id = required(authenticated_node_id, "authenticated_node_id")
    validated_handle = validate_workspace_handle(workspace_handle)
    if workspace_generation < 1:
        raise ValueError("workspace_generation must be positive")
    timestamp = now_iso()

    with db(immediate=True) as conn:
        row = conn.execute(
            """SELECT workspace.*, node.status AS node_status
               FROM compute_game_workspaces AS workspace
               JOIN compute_nodes AS node ON node.node_id = workspace.node_id
               WHERE workspace.project_id = ? AND workspace.resource_id = ?""",
            (project_id, resource_id),
        ).fetchone()
        if row is None:
            raise GameResourceError("game_resource_not_found")
        if row["status"] == "revoked":
            raise GameResourceError("game_resource_revoked")
        if (
            row["node_id"] != authenticated_node_id
            or row["workspace_handle"] != validated_handle
            or row["generation"] != workspace_generation
        ):
            raise GameResourceError("game_workspace_confirmation_mismatch")
        if row["node_status"] not in EXECUTABLE_NODE_STATUSES:
            raise GameResourceError("compute_node_unavailable")
        active_approval(
            conn,
            approval_id=row["isolation_approval_id"],
            node_id=row["node_id"],
            isolation_profile_id=row["isolation_profile_id"],
            runner_version=row["runner_version"],
            policy_digest=row["policy_digest"],
        )
        conn.execute(
            """UPDATE compute_game_workspaces
               SET status = 'ready', last_seen_at = ?, updated_at = ?
               WHERE project_id = ? AND resource_id = ?""",
            (timestamp, timestamp, project_id, resource_id),
        )
        audit.record_in_connection(
            conn,
            actor=f"node:{authenticated_node_id}",
            action="game.workspace.confirmed",
            node_id=authenticated_node_id,
            details={
                "resource_id": resource_id,
                "project_id": project_id,
                "generation": workspace_generation,
            },
        )
    confirmed = get_workspace(project_id, resource_id)
    if confirmed is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("confirmed game workspace could not be read back")
    return confirmed


def revoke_workspace(*, project_id: str, resource_id: str, actor: str) -> ComputeGameWorkspace:
    actor = required(actor, "actor")
    timestamp = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute(
            "SELECT * FROM compute_game_workspaces WHERE project_id = ? AND resource_id = ?",
            (project_id, resource_id),
        ).fetchone()
        if row is None:
            raise GameResourceError("game_resource_not_found")
        current = workspace_from_row(row)
        if current.status == "revoked":
            return current
        conn.execute(
            """UPDATE compute_game_workspaces
               SET status = 'revoked', revoked_at = ?, updated_at = ?
               WHERE project_id = ? AND resource_id = ?""",
            (timestamp, timestamp, project_id, resource_id),
        )
        audit.record_in_connection(
            conn,
            actor=actor,
            action="game.workspace.revoked",
            node_id=current.node_id,
            details={
                "resource_id": resource_id,
                "project_id": project_id,
                "generation": current.generation,
            },
        )
    revoked = get_workspace(project_id, resource_id)
    if revoked is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("revoked game workspace could not be read back")
    return revoked
