"""Atomic generation rotation for Game Studio workspace resources."""

from __future__ import annotations

from hydrahive.compute import audit
from hydrahive.compute._game_approvals import active_approval
from hydrahive.compute._game_resource_common import (
    MAX_DIGEST,
    MAX_VERSION,
    GameResourceError,
    engine as validate_engine,
    normalize_engine_project_relpath,
    optional_version,
    required,
    trust_mode as validate_trust_mode,
    workspace_from_row,
    workspace_handle as validate_workspace_handle,
)
from hydrahive.compute._game_workspaces import get_workspace
from hydrahive.compute.models import ComputeGameWorkspace
from hydrahive.db._utils import now_iso
from hydrahive.db.connection import db


def rotate_workspace(
    *,
    project_id: str,
    resource_id: str,
    workspace_handle: str,
    isolation_approval_id: str,
    isolation_profile_id: str,
    runner_version: str,
    policy_digest: str,
    actor: str,
    engine: str | None = None,
    engine_version: str | None = None,
    engine_project_relpath: str | None = None,
    trust_mode: str | None = None,
) -> ComputeGameWorkspace:
    project_id = required(project_id, "project_id")
    resource_id = required(resource_id, "resource_id")
    validated_handle = validate_workspace_handle(workspace_handle)
    isolation_approval_id = required(isolation_approval_id, "isolation_approval_id")
    isolation_profile_id = required(isolation_profile_id, "isolation_profile_id")
    runner_version = required(runner_version, "runner_version", maximum=MAX_VERSION)
    policy_digest = required(policy_digest, "policy_digest", maximum=MAX_DIGEST)
    actor = required(actor, "actor")
    timestamp = now_iso()

    with db(immediate=True) as conn:
        current_row = conn.execute(
            "SELECT * FROM compute_game_workspaces WHERE project_id = ? AND resource_id = ?",
            (project_id, resource_id),
        ).fetchone()
        if current_row is None:
            raise GameResourceError("game_resource_not_found")
        current = workspace_from_row(current_row)
        if current.status == "revoked":
            raise GameResourceError("game_resource_revoked")
        active_approval(
            conn,
            approval_id=isolation_approval_id,
            node_id=current.node_id,
            isolation_profile_id=isolation_profile_id,
            runner_version=runner_version,
            policy_digest=policy_digest,
        )
        next_engine = validate_engine(engine) if engine is not None else current.engine
        next_engine_version = optional_version(engine_version) if engine is not None else current.engine_version
        next_path = (
            normalize_engine_project_relpath(engine_project_relpath)
            if engine_project_relpath is not None
            else current.engine_project_relpath
        )
        next_trust_mode = validate_trust_mode(trust_mode) if trust_mode is not None else current.trust_mode
        next_generation = current.generation + 1
        conn.execute(
            """UPDATE compute_game_workspaces
               SET workspace_handle = ?, engine = ?, engine_version = ?,
                   engine_project_relpath = ?, trust_mode = ?, status = 'pending',
                   isolation_approval_id = ?, isolation_profile_id = ?, runner_version = ?,
                   policy_digest = ?, generation = ?, updated_at = ?, last_seen_at = NULL
               WHERE project_id = ? AND resource_id = ?""",
            (
                validated_handle,
                next_engine,
                next_engine_version,
                next_path,
                next_trust_mode,
                isolation_approval_id,
                isolation_profile_id,
                runner_version,
                policy_digest,
                next_generation,
                timestamp,
                project_id,
                resource_id,
            ),
        )
        audit.record_in_connection(
            conn,
            actor=actor,
            action="game.workspace.rotated",
            node_id=current.node_id,
            details={
                "resource_id": resource_id,
                "project_id": project_id,
                "previous_generation": current.generation,
                "generation": next_generation,
                "isolation_approval_id": isolation_approval_id,
                "status": "pending",
            },
        )
    rotated = get_workspace(project_id, resource_id)
    if rotated is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("rotated game workspace could not be read back")
    return rotated
