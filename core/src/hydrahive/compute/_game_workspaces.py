"""Creation and project-scoped reads for Game Studio workspaces."""

from __future__ import annotations

from hydrahive.compute import audit
from hydrahive.compute._game_approvals import active_approval
from hydrahive.compute._game_resource_common import (
    MAX_DIGEST,
    MAX_VERSION,
    engine as validate_engine,
    normalize_engine_project_relpath,
    optional_version,
    required,
    trust_mode as validate_trust_mode,
    workspace_from_row,
    workspace_handle as validate_workspace_handle,
)
from hydrahive.compute.models import GAME_RUNTIME_PROVIDER, ComputeGameWorkspace
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db


def get_workspace(project_id: str, resource_id: str) -> ComputeGameWorkspace | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM compute_game_workspaces WHERE project_id = ? AND resource_id = ?",
            (project_id, resource_id),
        ).fetchone()
    return workspace_from_row(row) if row else None


def list_workspaces(project_id: str) -> list[ComputeGameWorkspace]:
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM compute_game_workspaces WHERE project_id = ?
               ORDER BY generation DESC, created_at DESC""",
            (project_id,),
        ).fetchall()
    return [workspace_from_row(row) for row in rows]


def create_workspace(
    *,
    project_id: str,
    node_id: str,
    workspace_handle: str,
    engine: str,
    engine_version: str | None,
    engine_project_relpath: str = ".",
    trust_mode: str,
    isolation_approval_id: str,
    isolation_profile_id: str,
    runner_version: str,
    policy_digest: str,
    created_by: str,
) -> ComputeGameWorkspace:
    project_id = required(project_id, "project_id")
    node_id = required(node_id, "node_id")
    workspace_handle_value = validate_workspace_handle(workspace_handle)
    validated_engine = validate_engine(engine)
    engine_version = optional_version(engine_version)
    engine_project_relpath = normalize_engine_project_relpath(engine_project_relpath)
    validated_trust_mode = validate_trust_mode(trust_mode)
    isolation_approval_id = required(isolation_approval_id, "isolation_approval_id")
    isolation_profile_id = required(isolation_profile_id, "isolation_profile_id")
    runner_version = required(runner_version, "runner_version", maximum=MAX_VERSION)
    policy_digest = required(policy_digest, "policy_digest", maximum=MAX_DIGEST)
    created_by = required(created_by, "created_by")
    resource_id = uuid7()
    timestamp = now_iso()

    with db(immediate=True) as conn:
        active_approval(
            conn,
            approval_id=isolation_approval_id,
            node_id=node_id,
            isolation_profile_id=isolation_profile_id,
            runner_version=runner_version,
            policy_digest=policy_digest,
        )
        generation = conn.execute(
            "SELECT COALESCE(MAX(generation), 0) + 1 FROM compute_game_workspaces WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]
        previous = conn.execute(
            """SELECT resource_id FROM compute_game_workspaces
               WHERE project_id = ? AND status != 'revoked' AND revoked_at IS NULL""",
            (project_id,),
        ).fetchall()
        conn.execute(
            """UPDATE compute_game_workspaces
               SET status = 'revoked', revoked_at = ?, updated_at = ?
               WHERE project_id = ? AND status != 'revoked' AND revoked_at IS NULL""",
            (timestamp, timestamp, project_id),
        )
        conn.execute(
            """INSERT INTO compute_game_workspaces
                   (resource_id, provider, project_id, node_id, workspace_handle,
                    engine, engine_version, engine_project_relpath, trust_mode, status,
                    isolation_approval_id, isolation_profile_id, runner_version,
                    policy_digest, generation, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                resource_id,
                GAME_RUNTIME_PROVIDER,
                project_id,
                node_id,
                workspace_handle_value,
                validated_engine,
                engine_version,
                engine_project_relpath,
                validated_trust_mode,
                isolation_approval_id,
                isolation_profile_id,
                runner_version,
                policy_digest,
                generation,
                created_by,
                timestamp,
                timestamp,
            ),
        )
        audit.record_in_connection(
            conn,
            actor=created_by,
            action="game.workspace.bound",
            node_id=node_id,
            details={
                "resource_id": resource_id,
                "project_id": project_id,
                "generation": generation,
                "isolation_approval_id": isolation_approval_id,
                "replaced_resource_ids": [row["resource_id"] for row in previous],
                "status": "pending",
            },
        )
    created = get_workspace(project_id, resource_id)
    if created is None:  # pragma: no cover - transactional invariant
        raise RuntimeError("created game workspace could not be read back")
    return created
