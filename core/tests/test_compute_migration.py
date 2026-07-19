from __future__ import annotations

import sqlite3
from pathlib import Path

from hydrahive.db.migrations import apply_migrations

MIGRATIONS_DIR = Path(__file__).parents[1] / "src" / "hydrahive" / "db" / "migrations"


def _apply_through_031(conn: sqlite3.Connection) -> None:
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if migration.name.startswith("032_"):
            continue
        conn.executescript(migration.read_text())


def test_migration_creates_compute_schema_and_local_node_once(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        apply_migrations(conn)
        apply_migrations(conn)

        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {
            "compute_nodes",
            "compute_enrollment_tokens",
            "compute_jobs",
            "compute_job_events",
        } <= tables
        expected_columns = {
            "compute_nodes": {
                "node_id",
                "name",
                "kind",
                "status",
                "certificate_fingerprint",
                "protocol_version",
                "agent_version",
                "capabilities_json",
                "resources_json",
                "labels_json",
                "last_seen_at",
                "approved_at",
                "approved_by",
                "revoked_at",
                "created_at",
                "updated_at",
            },
            "compute_enrollment_tokens": {
                "token_id",
                "token_hmac",
                "requested_name",
                "expires_at",
                "consumed_at",
                "created_by",
                "created_at",
            },
            "compute_jobs": {
                "job_id",
                "node_id",
                "resource_kind",
                "resource_id",
                "operation",
                "generation",
                "payload_json",
                "idempotency_key",
                "status",
                "lease_id",
                "lease_until",
                "attempts",
                "progress",
                "error_code",
                "error_params_json",
                "created_by",
                "created_at",
                "started_at",
                "finished_at",
            },
            "compute_job_events": {
                "event_id",
                "job_id",
                "sequence",
                "event_type",
                "data_json",
                "created_at",
            },
        }
        for table, columns in expected_columns.items():
            actual = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            assert actual == columns

        local_nodes = conn.execute(
            "SELECT node_id, name, kind, status FROM compute_nodes WHERE node_id = 'local'"
        ).fetchall()
        assert [tuple(row) for row in local_nodes] == [("local", "Local Host", "local", "online")]
    finally:
        conn.close()


def test_migration_backfills_existing_resources(tmp_path: Path) -> None:
    conn = sqlite3.connect(tmp_path / "backfill.db")
    conn.row_factory = sqlite3.Row
    try:
        _apply_through_031(conn)
        conn.execute(
            """INSERT INTO containers
                   (container_id, owner, name, image, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("container-1", "owner", "existing-container", "images:debian/12", "before", "before"),
        )
        conn.execute(
            """INSERT INTO vms
                   (vm_id, owner, name, cpu, ram_mb, disk_gb, qcow2_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("vm-1", "owner", "existing-vm", 2, 2048, 20, "/tmp/vm.qcow2", "before", "before"),
        )

        conn.executescript((MIGRATIONS_DIR / "032_compute_nodes.sql").read_text())

        container = conn.execute(
            "SELECT node_id, generation FROM containers WHERE container_id = ?",
            ("container-1",),
        ).fetchone()
        vm = conn.execute("SELECT node_id, generation FROM vms WHERE vm_id = ?", ("vm-1",)).fetchone()
        assert tuple(container) == ("local", 0)
        assert tuple(vm) == ("local", 0)
    finally:
        conn.close()
