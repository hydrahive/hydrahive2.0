from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import game_resources
from hydrahive.compute.models import ExecutionBinding
from hydrahive.db.connection import init_db
from hydrahive.projects import config as project_config
from hydrahive.settings import settings


@pytest.fixture
def game_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "game.db", raising=False)
    monkeypatch.setattr(
        project_config,
        "get",
        lambda project_id: {"id": project_id, "status": "active"},
    )
    init_db()
    node_db.create_node(
        node_id="game-node",
        name="Game Node",
        certificate_fingerprint="ab" * 32,
    )
    node_db.approve_node("game-node", "admin-user-id")
    node_db.transition_node_status("game-node", "online")


def _approval():
    return game_resources.approve_isolation(
        node_id="game-node",
        isolation_profile_id="linux-microvm-v1",
        runner_version="1.0.0",
        policy_digest="sha256:policy-v1",
        proof_digest="sha256:proof-v1",
        approved_by="admin-user-id",
    )


def _workspace(*, project_id: str = "project-a", handle: str = "opaque-handle-a"):
    approval = _approval()
    workspace = game_resources.create_workspace(
        project_id=project_id,
        node_id="game-node",
        workspace_handle=handle,
        engine="godot",
        engine_version="4.5.1",
        engine_project_relpath=".",
        trust_mode="sandboxed",
        isolation_approval_id=approval.approval_id,
        isolation_profile_id=approval.isolation_profile_id,
        runner_version=approval.runner_version,
        policy_digest=approval.policy_digest,
        created_by="project-admin-user-id",
    )
    return approval, workspace


def _binding(approval, workspace, **changes) -> ExecutionBinding:
    values = {
        "project_id": workspace.project_id,
        "resource_id": workspace.resource_id,
        "node_id": workspace.node_id,
        "workspace_handle": workspace.workspace_handle,
        "workspace_generation": workspace.generation,
        "isolation_approval_id": workspace.isolation_approval_id,
        "isolation_profile_id": workspace.isolation_profile_id,
        "runner_version": workspace.runner_version,
        "policy_digest": workspace.policy_digest,
        "proof_digest": approval.proof_digest,
    }
    values.update(changes)
    return ExecutionBinding(**values)


def test_browser_created_workspace_is_pending_until_internal_node_confirmation(game_db: None) -> None:
    approval, workspace = _workspace()

    assert workspace.status == "pending"
    with pytest.raises(game_resources.ExecutionBindingError) as pending:
        game_resources.validate_execution_binding(_binding(approval, workspace))
    assert pending.value.code == "game_resource_not_ready"

    confirmed = game_resources.confirm_workspace(
        project_id=workspace.project_id,
        resource_id=workspace.resource_id,
        authenticated_node_id=workspace.node_id,
        workspace_handle=workspace.workspace_handle,
        workspace_generation=workspace.generation,
    )
    assert confirmed.status == "ready"
    assert game_resources.validate_execution_binding(_binding(approval, confirmed)) == confirmed


def test_execution_binding_fails_closed_for_every_security_dimension(game_db: None) -> None:
    approval, pending = _workspace()
    workspace = game_resources.confirm_workspace(
        project_id=pending.project_id,
        resource_id=pending.resource_id,
        authenticated_node_id=pending.node_id,
        workspace_handle=pending.workspace_handle,
        workspace_generation=pending.generation,
    )

    mismatches = {
        "project_id": "project-b",
        "node_id": "another-node",
        "workspace_handle": "another-handle",
        "workspace_generation": workspace.generation + 1,
        "isolation_approval_id": "another-approval",
        "isolation_profile_id": "another-profile",
        "runner_version": "2.0.0",
        "policy_digest": "sha256:another-policy",
        "proof_digest": "sha256:another-proof",
    }
    for field, value in mismatches.items():
        with pytest.raises(game_resources.ExecutionBindingError):
            game_resources.validate_execution_binding(_binding(approval, workspace, **{field: value}))


def test_execution_binding_rejects_deleted_core_project(
    game_db: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approval, pending = _workspace()
    workspace = game_resources.confirm_workspace(
        project_id=pending.project_id,
        resource_id=pending.resource_id,
        authenticated_node_id=pending.node_id,
        workspace_handle=pending.workspace_handle,
        workspace_generation=pending.generation,
    )
    monkeypatch.setattr(project_config, "get", lambda project_id: None)

    with pytest.raises(game_resources.ExecutionBindingError) as deleted:
        game_resources.validate_execution_binding(_binding(approval, workspace))

    assert deleted.value.code == "project_not_found"


def test_rebind_revokes_old_resource_and_increments_project_generation(game_db: None) -> None:
    approval, original = _workspace()
    rebound = game_resources.create_workspace(
        project_id=original.project_id,
        node_id=original.node_id,
        workspace_handle="opaque-handle-b",
        engine="godot",
        engine_version="4.5.1",
        engine_project_relpath="game",
        trust_mode="sandboxed",
        isolation_approval_id=approval.approval_id,
        isolation_profile_id=approval.isolation_profile_id,
        runner_version=approval.runner_version,
        policy_digest=approval.policy_digest,
        created_by="project-admin-user-id",
    )

    assert rebound.generation == 2
    assert rebound.status == "pending"
    revoked = game_resources.get_workspace(original.project_id, original.resource_id)
    assert revoked is not None
    assert revoked.status == "revoked"
    assert revoked.revoked_at is not None


def test_rotation_is_atomic_and_returns_to_pending(game_db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    approval, workspace = _workspace()
    original = workspace

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(game_resources.audit, "record_in_connection", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        game_resources.rotate_workspace(
            project_id=workspace.project_id,
            resource_id=workspace.resource_id,
            workspace_handle="opaque-rotated",
            isolation_approval_id=approval.approval_id,
            isolation_profile_id=approval.isolation_profile_id,
            runner_version=approval.runner_version,
            policy_digest=approval.policy_digest,
            actor="project-admin-user-id",
        )

    assert game_resources.get_workspace(workspace.project_id, workspace.resource_id) == original


@pytest.mark.parametrize(
    "path",
    ["", "/absolute", "../escape", "game/../escape", "game//scene", "game/./scene", "game/", r"C:\\game"],
)
def test_engine_project_relative_path_rejects_unsafe_values(game_db: None, path: str) -> None:
    with pytest.raises(ValueError, match="engine_project_relpath"):
        game_resources.normalize_engine_project_relpath(path)


def test_engine_project_relative_path_allows_root_default_and_normal_relative_path(game_db: None) -> None:
    assert game_resources.normalize_engine_project_relpath(".") == "."
    assert game_resources.normalize_engine_project_relpath("game/scenes") == "game/scenes"
