from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import game_resources, job_protocol, job_signing, jobs
from hydrahive.compute.channel_message import AgentMessage
from hydrahive.db.connection import db, init_db
from hydrahive.projects import config as project_config
from hydrahive.settings import settings

DIGEST = "sha256:" + "b" * 64
SOURCE_COMMIT = "a" * 40


@pytest.fixture
def game_jobs_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "game-jobs.db", raising=False)
    monkeypatch.setattr(settings, "compute_pki_dir", tmp_path / "pki", raising=False)
    monkeypatch.setattr(project_config, "get", lambda project_id: {"id": project_id, "status": "active"})
    init_db()
    node_db.create_node(node_id="game-node", name="Game Node", certificate_fingerprint="ab" * 32)
    node_db.approve_node("game-node", "admin-user-id")
    node_db.transition_node_status("game-node", "online")
    approval = game_resources.approve_isolation(
        node_id="game-node",
        isolation_profile_id="linux-microvm-v1",
        runner_version="1.0.0",
        policy_digest="sha256:policy-v1",
        proof_digest="sha256:proof-v1",
        approved_by="admin-user-id",
    )
    pending = game_resources.create_workspace(
        project_id="project-a",
        node_id="game-node",
        workspace_handle="opaque-workspace-a",
        engine="godot",
        engine_version="4.5.1",
        engine_project_relpath=".",
        trust_mode="sandboxed",
        isolation_approval_id=approval.approval_id,
        isolation_profile_id=approval.isolation_profile_id,
        runner_version=approval.runner_version,
        policy_digest=approval.policy_digest,
        created_by="project-admin-id",
    )
    workspace = game_resources.confirm_workspace(
        project_id="project-a",
        resource_id=pending.resource_id,
        authenticated_node_id="game-node",
        workspace_handle=pending.workspace_handle,
        workspace_generation=pending.generation,
    )
    return {"approval": approval, "workspace": workspace}


def _request(resource_id: str, *, key: str = "game-request-a", operation: str = "game.project.validate") -> dict:
    payloads = {
        "game.project.validate": {"validation_profile_id": "validation-default"},
        "game.project.build": {"target_id": "linux", "configuration_id": "debug"},
    }
    return {
        "game_resource_id": resource_id,
        "operation": operation,
        "source_commit_sha": SOURCE_COMMIT,
        "source_snapshot_digest": None,
        "inventory_snapshot_id": "inventory-a",
        "engine": "godot",
        "engine_version": "4.5.1",
        "toolchain_digest": DIGEST,
        "profile_id": "debug-desktop",
        "input_revision": 12,
        "limits": {
            "timeout_seconds": 900,
            "cpu_cores": 4,
            "memory_mb": 8192,
            "disk_mb": 16384,
            "pids": 256,
            "network": "off",
        },
        "operation_payload": payloads[operation],
        "idempotency_key": key,
    }


def _create(context: dict, *, key: str = "game-request-a"):
    return jobs.create_game_job(
        project_id="project-a",
        request=_request(context["workspace"].resource_id, key=key),
        created_by="immutable-user-id",
    )


def test_game_job_store_persists_exact_bindings_and_scopes_by_project(game_jobs_context: dict) -> None:
    created = _create(game_jobs_context)

    assert created.resource_kind == "game_workspace"
    assert created.project_id == "project-a"
    assert created.provider == "game-runtime/v1"
    assert created.game_resource_id == game_jobs_context["workspace"].resource_id
    assert created.workspace_generation == game_jobs_context["workspace"].generation
    assert created.source_commit_sha == SOURCE_COMMIT
    assert created.source_snapshot_digest is None
    assert created.created_by == "immutable-user-id"
    assert jobs.get_project_job("project-a", created.job_id) == created
    assert jobs.get_project_job("project-b", created.job_id) is None
    assert jobs.list_project_jobs("project-a") == [created]


def test_game_job_creation_revalidates_pr1_binding_before_queue(game_jobs_context: dict) -> None:
    workspace = game_jobs_context["workspace"]
    with db() as conn:
        conn.execute(
            """UPDATE compute_game_workspaces
               SET status = 'revoked', revoked_at = 'now' WHERE resource_id = ?""",
            (workspace.resource_id,),
        )

    with pytest.raises(game_resources.ExecutionBindingError):
        jobs.create_game_job(
            project_id="project-a",
            request=_request(workspace.resource_id),
            created_by="immutable-user-id",
        )

    assert jobs.list_project_jobs("project-a") == []


def test_game_job_lease_rejects_binding_changed_after_queue(game_jobs_context: dict) -> None:
    created = _create(game_jobs_context)
    with db() as conn:
        conn.execute(
            "UPDATE compute_game_workspaces SET workspace_handle = 'changed-handle' WHERE resource_id = ?",
            (created.game_resource_id,),
        )

    assert jobs.claim_next_job(created.node_id) is None
    rejected = jobs.get_job(created.job_id)
    assert rejected is not None
    assert rejected.status == "failed"
    assert rejected.error_code == "job_rejected"


def test_game_job_pre_start_gate_rejects_changed_binding(game_jobs_context: dict) -> None:
    created = _create(game_jobs_context)
    claimed = jobs.claim_next_job(created.node_id)
    assert claimed is not None and claimed.lease_id
    with db() as conn:
        conn.execute(
            "UPDATE compute_game_workspaces SET workspace_handle = 'changed-handle' WHERE resource_id = ?",
            (created.game_resource_id,),
        )

    rejected = job_protocol.handle_message(
        created.node_id,
        "job_started",
        {"job_id": created.job_id, "lease_id": claimed.lease_id},
    )

    assert rejected == {"type": "job_rejected", "reason": "execution_binding_invalid"}
    assert jobs.get_job(created.job_id).status == "failed"


def test_game_job_offer_is_canonical_signed_and_covers_all_persisted_bindings(game_jobs_context: dict) -> None:
    created = _create(game_jobs_context)
    response = job_protocol.handle_message(created.node_id, "job_poll", {})
    offer = response["job"]

    assert offer["provider"] == "game-runtime/v1"
    assert offer["project_id"] == "project-a"
    assert offer["game_resource_id"] == created.game_resource_id
    assert offer["workspace_generation"] == created.workspace_generation
    assert offer["attempt_id"] == offer["lease_id"]
    assert offer["source_commit_sha"] == SOURCE_COMMIT
    assert job_signing.verify_offer(offer, response["signature"], job_signing.public_key_text())

    tampered = dict(offer, source_commit_sha="c" * 40)
    assert not job_signing.verify_offer(tampered, response["signature"], job_signing.public_key_text())


@pytest.mark.parametrize("message_type", ["job_control_poll", "job_cancelled"])
def test_compute_channel_schema_accepts_game_control_messages(message_type: str) -> None:
    message = AgentMessage.model_validate(
        {
            "type": message_type,
            "protocol_version": 1,
            "node_id": "game-node",
            "sequence": 1,
            "nonce": "nonce-game-control-01",
            "sent_at": "2099-01-01T00:00:00Z",
            "payload": {},
        }
    )

    assert message.type == message_type


def test_running_game_job_gets_cancel_directive_when_execution_binding_is_revoked(
    game_jobs_context: dict,
) -> None:
    created = _create(game_jobs_context)
    offer = job_protocol.handle_message(created.node_id, "job_poll", {})
    lease_id = offer["job"]["lease_id"]
    assert job_protocol.handle_message(
        created.node_id, "job_started", {"job_id": created.job_id, "lease_id": lease_id}
    ) == {"type": "ack"}

    game_resources.revoke_isolation_approval(
        game_jobs_context["approval"].approval_id,
        revoked_by="immutable-admin-id",
    )
    control = job_protocol.handle_message(created.node_id, "job_control_poll", {})

    assert control["type"] == "job_cancel"
    invalidated = jobs.get_job(created.job_id)
    assert invalidated is not None
    assert invalidated.status == "running"
    assert invalidated.cancel_requested_by == "system:binding-invalidated"


def test_running_game_cancel_uses_signed_control_plane_and_terminal_node_confirmation(
    game_jobs_context: dict,
) -> None:
    created = _create(game_jobs_context)
    offer = job_protocol.handle_message(created.node_id, "job_poll", {})
    lease_id = offer["job"]["lease_id"]
    assert job_protocol.handle_message(
        created.node_id, "job_started", {"job_id": created.job_id, "lease_id": lease_id}
    ) == {"type": "ack"}

    requested = jobs.cancel_job(created.job_id, actor="immutable-user-id")
    assert requested.status == "running"
    assert requested.cancel_requested_by == "immutable-user-id"
    control = job_protocol.handle_message(created.node_id, "job_control_poll", {})
    assert control["type"] == "job_cancel"
    assert control["job_id"] == created.job_id
    signed = {key: control[key] for key in ("job_id", "node_id", "lease_id", "cancel_deadline")}
    assert job_signing.verify_offer(signed, control["signature"], job_signing.public_key_text())

    wrong = job_protocol.handle_message(
        created.node_id,
        "job_cancelled",
        {"job_id": created.job_id, "lease_id": "wrong-lease"},
    )
    assert wrong == {"type": "job_rejected", "reason": "state_conflict"}
    confirmed = job_protocol.handle_message(
        created.node_id,
        "job_cancelled",
        {"job_id": created.job_id, "lease_id": lease_id},
    )
    assert confirmed == {"type": "ack"}
    assert jobs.get_job(created.job_id).status == "cancelled"
