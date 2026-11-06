from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import audit
from hydrahive.compute import db as node_db
from hydrahive.compute import game_resources
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def game_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "game-revoke.db", raising=False)
    init_db()
    node_db.create_node(
        node_id="game-node-revoke",
        name="Game Node Revoke",
        certificate_fingerprint="cd" * 32,
    )
    node_db.approve_node("game-node-revoke", "admin-user-id")
    node_db.transition_node_status("game-node-revoke", "online")


def _active_records():
    approval = game_resources.approve_isolation(
        node_id="game-node-revoke",
        isolation_profile_id="linux-microvm-v1",
        runner_version="1.0.0",
        policy_digest="sha256:policy-v1",
        proof_digest="sha256:proof-v1",
        approved_by="admin-user-id",
    )
    workspace = game_resources.create_workspace(
        project_id="project-revoke",
        node_id="game-node-revoke",
        workspace_handle="opaque-revoke",
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


def test_approval_revoke_atomically_invalidates_dependent_binding_and_audits(game_db: None) -> None:
    approval, workspace = _active_records()

    revoked = game_resources.revoke_isolation_approval(
        approval.approval_id,
        revoked_by="immutable-admin-user-id",
    )

    assert revoked.status == "revoked"
    assert revoked.revoked_by == "immutable-admin-user-id"
    invalidated = game_resources.get_workspace(workspace.project_id, workspace.resource_id)
    assert invalidated is not None
    assert invalidated.status == "revoked"
    records = audit.list_records(node_id=workspace.node_id)
    record = next(item for item in records if item["action"] == "game.isolation_approval.revoked")
    assert record["actor"] == "immutable-admin-user-id"
    assert record["details"]["invalidated_resources"] == 1


def test_node_revoke_invalidates_active_approvals_and_bindings_in_same_transaction(game_db: None) -> None:
    approval, workspace = _active_records()

    node_db.revoke_node(workspace.node_id, actor="immutable-admin-user-id")

    invalidated = game_resources.get_workspace(workspace.project_id, workspace.resource_id)
    assert invalidated is not None
    assert invalidated.status == "revoked"
    revoked_approval = game_resources.get_isolation_approval(approval.approval_id)
    assert revoked_approval is not None
    assert revoked_approval.status == "revoked"
    assert revoked_approval.revoked_by == "immutable-admin-user-id"


def test_physical_node_delete_reports_in_use_for_game_records(game_db: None) -> None:
    _active_records()

    with pytest.raises(ValueError, match="in use"):
        node_db.delete_node("game-node-revoke")


def test_revoke_rolls_back_state_when_audit_write_fails(
    game_db: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approval, workspace = _active_records()

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(game_resources.audit, "record_in_connection", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        game_resources.revoke_workspace(
            project_id=workspace.project_id,
            resource_id=workspace.resource_id,
            actor="project-admin-user-id",
        )

    unchanged = game_resources.get_workspace(workspace.project_id, workspace.resource_id)
    assert unchanged is not None
    assert unchanged.status == "pending"
    assert unchanged.revoked_at is None
    assert game_resources.get_isolation_approval(approval.approval_id).status == "active"
