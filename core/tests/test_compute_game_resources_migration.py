from __future__ import annotations

import sqlite3
from pathlib import Path

from hydrahive.db.migrations import apply_migrations


def test_migration_057_creates_game_workspace_and_approval_schema(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "game-resources.db")
    conn.row_factory = sqlite3.Row
    try:
        apply_migrations(conn)
        apply_migrations(conn)

        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        assert version == 57

        approval_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(compute_game_isolation_approvals)")
        }
        assert approval_columns == {
            "approval_id",
            "node_id",
            "isolation_profile_id",
            "runner_version",
            "policy_digest",
            "proof_digest",
            "status",
            "approved_by",
            "approved_at",
            "revoked_by",
            "revoked_at",
        }

        workspace_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(compute_game_workspaces)")
        }
        assert workspace_columns == {
            "resource_id",
            "provider",
            "project_id",
            "node_id",
            "workspace_handle",
            "engine",
            "engine_version",
            "engine_project_relpath",
            "trust_mode",
            "status",
            "isolation_approval_id",
            "isolation_profile_id",
            "runner_version",
            "policy_digest",
            "generation",
            "created_by",
            "created_at",
            "updated_at",
            "last_seen_at",
            "revoked_at",
        }
        assert not ({"absolute_path", "host_path", "secret", "credentials"} & workspace_columns)

        indexes = {
            row["name"]: row["sql"]
            for row in conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'compute_game_workspaces'"
            )
        }
        active_index = indexes["uq_compute_game_workspaces_active_project"]
        assert "UNIQUE" in active_index
        assert "WHERE" in active_index

        node_delete_trigger = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'compute_nodes_restrict_delete'"
        ).fetchone()["sql"]
        assert "compute_jobs" in node_delete_trigger
        assert "compute_game_workspaces" in node_delete_trigger
        assert "compute_game_isolation_approvals" in node_delete_trigger
    finally:
        conn.close()


def test_migration_057_restricts_physical_node_delete_when_game_records_exist(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "game-node-delete.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        apply_migrations(conn)
        conn.execute(
            """INSERT INTO compute_nodes
               (node_id, name, kind, status, protocol_version, capabilities_json,
                resources_json, labels_json, created_at, updated_at)
               VALUES ('game-node', 'Game Node', 'agent', 'pending', 1, '{}', '{}', '{}', 'now', 'now')"""
        )
        conn.execute(
            """INSERT INTO compute_game_isolation_approvals
               (approval_id, node_id, isolation_profile_id, runner_version,
                policy_digest, proof_digest, status, approved_by, approved_at)
               VALUES ('approval', 'game-node', 'microvm-v1', '1.0.0',
                       'sha256:policy', 'sha256:proof', 'active', 'user-id', 'now')"""
        )

        try:
            conn.execute("DELETE FROM compute_nodes WHERE node_id = 'game-node'")
        except sqlite3.IntegrityError as exc:
            assert "compute_node_in_use" in str(exc)
        else:  # pragma: no cover - documents the required database invariant
            raise AssertionError("physical node delete unexpectedly succeeded")
    finally:
        conn.close()
