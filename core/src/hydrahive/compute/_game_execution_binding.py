"""Fail-closed execution-binding contract reserved for PR2 integration."""

from __future__ import annotations

from hydrahive.compute._game_resource_common import (
    EXECUTABLE_NODE_STATUSES,
    ExecutionBindingError,
    workspace_from_row,
)
from hydrahive.compute.models import ComputeGameWorkspace, ExecutionBinding
from hydrahive.db.connection import db
from hydrahive.projects import config as project_config


def validate_execution_binding(binding: ExecutionBinding) -> ComputeGameWorkspace:
    """Validate every security dimension required before PR2 queue/lease/start."""
    with db() as conn:
        row = conn.execute(
            """SELECT workspace.*, approval.proof_digest AS approval_proof_digest,
                      approval.status AS approval_status,
                      approval.node_id AS approval_node_id,
                      approval.isolation_profile_id AS approval_profile_id,
                      approval.runner_version AS approval_runner_version,
                      approval.policy_digest AS approval_policy_digest,
                      node.status AS node_status
               FROM compute_game_workspaces AS workspace
               JOIN compute_game_isolation_approvals AS approval
                 ON approval.approval_id = workspace.isolation_approval_id
               JOIN compute_nodes AS node ON node.node_id = workspace.node_id
               WHERE workspace.project_id = ? AND workspace.resource_id = ?""",
            (binding.project_id, binding.resource_id),
        ).fetchone()
    if row is None:
        raise ExecutionBindingError("game_resource_not_found")
    if project_config.get(binding.project_id) is None:
        raise ExecutionBindingError("project_not_found")
    if row["status"] != "ready":
        raise ExecutionBindingError("game_resource_not_ready")
    if row["node_status"] not in EXECUTABLE_NODE_STATUSES:
        raise ExecutionBindingError("compute_node_unavailable")
    expected = {
        "node_id": binding.node_id,
        "workspace_handle": binding.workspace_handle,
        "generation": binding.workspace_generation,
        "isolation_approval_id": binding.isolation_approval_id,
        "isolation_profile_id": binding.isolation_profile_id,
        "runner_version": binding.runner_version,
        "policy_digest": binding.policy_digest,
    }
    if any(row[field] != value for field, value in expected.items()):
        raise ExecutionBindingError("game_execution_binding_mismatch")
    if (
        row["approval_status"] != "active"
        or row["approval_node_id"] != binding.node_id
        or row["approval_profile_id"] != binding.isolation_profile_id
        or row["approval_runner_version"] != binding.runner_version
        or row["approval_policy_digest"] != binding.policy_digest
        or row["approval_proof_digest"] != binding.proof_digest
    ):
        raise ExecutionBindingError("game_isolation_approval_invalid")
    return workspace_from_row(row)
