from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hydrahive.db.migrations import MIGRATIONS_DIR, apply_migrations


def _apply_through(conn: sqlite3.Connection, maximum: int) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if int(migration.name.split("_", 1)[0]) > maximum:
            break
        conn.executescript(migration.read_text())


def test_migration_058_adds_strict_game_job_bindings_and_preserves_legacy_jobs(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "game-jobs-upgrade.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_through(conn, 57)
        conn.execute(
            """INSERT INTO compute_nodes
               (node_id, name, kind, status, protocol_version, capabilities_json,
                resources_json, labels_json, created_at, updated_at)
               VALUES ('node-a', 'Node A', 'agent', 'online', 1, '{}', '{}', '{}', 'now', 'now')"""
        )
        conn.execute(
            """INSERT INTO compute_jobs
               (job_id, node_id, resource_kind, resource_id, operation, generation,
                payload_json, idempotency_key, status, created_by, created_at)
               VALUES ('legacy-job', 'node-a', 'container', 'container-a', 'container.start', 1,
                       '{}', 'legacy-key', 'queued', 'user-a', 'now')"""
        )
        conn.execute(
            """INSERT INTO compute_job_events
               (job_id, sequence, event_type, data_json, created_at)
               VALUES ('legacy-job', 0, 'queued', '{}', 'now')"""
        )

        conn.executescript((MIGRATIONS_DIR / "058_compute_game_jobs.sql").read_text())

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(compute_jobs)")}
        assert {
            "project_id",
            "provider",
            "game_resource_id",
            "workspace_generation",
            "source_commit_sha",
            "source_snapshot_digest",
            "cancel_requested_by",
            "cancel_requested_at",
        } <= columns
        legacy = conn.execute("SELECT * FROM compute_jobs WHERE job_id = 'legacy-job'").fetchone()
        assert legacy["resource_kind"] == "container"
        assert legacy["project_id"] is None
        assert conn.execute(
            "SELECT event_type FROM compute_job_events WHERE job_id = 'legacy-job'"
        ).fetchone()[0] == "queued"
    finally:
        conn.close()


def test_migration_058_enforces_game_binding_shape_and_keeps_non_game_shape_valid(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "game-jobs-constraints.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        conn.execute(
            """INSERT INTO compute_nodes
               (node_id, name, kind, status, protocol_version, capabilities_json,
                resources_json, labels_json, created_at, updated_at)
               VALUES ('node-a', 'Node A', 'agent', 'online', 1, '{}', '{}', '{}', 'now', 'now')"""
        )
        conn.execute(
            """INSERT INTO compute_game_isolation_approvals
               (approval_id, node_id, isolation_profile_id, runner_version, policy_digest,
                proof_digest, status, approved_by, approved_at)
               VALUES ('approval-a', 'node-a', 'microvm-v1', '1.0.0', 'sha256:policy',
                       'sha256:proof', 'active', 'admin-id', 'now')"""
        )
        conn.execute(
            """INSERT INTO compute_game_workspaces
               (resource_id, project_id, node_id, workspace_handle, engine, trust_mode, status,
                isolation_approval_id, isolation_profile_id, runner_version, policy_digest,
                generation, created_by, created_at, updated_at)
               VALUES ('resource-a', 'project-a', 'node-a', 'opaque-a', 'godot', 'sandboxed', 'ready',
                       'approval-a', 'microvm-v1', '1.0.0', 'sha256:policy', 3,
                       'user-a', 'now', 'now')"""
        )
        base = (
            "job-a", "node-a", "game_workspace", "resource-a", "game.project.validate", 3,
            "{}", "key-a", "queued", "user-a", "now", "project-a", "game-runtime/v1",
            "resource-a", 3, "a" * 40, None,
        )
        conn.execute(
            """INSERT INTO compute_jobs
               (job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
                idempotency_key, status, created_by, created_at, project_id, provider,
                game_resource_id, workspace_generation, source_commit_sha, source_snapshot_digest)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            base,
        )

        invalid = list(base)
        invalid[0] = "job-invalid-source"
        invalid[7] = "key-invalid-source"
        invalid[16] = "sha256:" + "b" * 64
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO compute_jobs
                   (job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
                    idempotency_key, status, created_by, created_at, project_id, provider,
                    game_resource_id, workspace_generation, source_commit_sha, source_snapshot_digest)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                invalid,
            )

        conn.execute(
            """INSERT INTO compute_jobs
               (job_id, node_id, resource_kind, resource_id, operation, generation, payload_json,
                idempotency_key, status, created_by, created_at)
               VALUES ('legacy-valid', 'node-a', 'vm', 'vm-a', 'vm.inspect', 0, '{}',
                       'legacy-valid', 'queued', 'user-a', 'now')"""
        )
    finally:
        conn.close()
