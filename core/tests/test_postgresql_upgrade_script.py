from __future__ import annotations

from pathlib import Path
import re
import subprocess


SCRIPT = Path(__file__).resolve().parents[2] / "installer" / "migrate-postgresql-cluster.sh"


def test_requires_explicit_confirmation() -> None:
    result = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True)

    assert result.returncode != 0
    assert "--yes" in result.stderr


def test_script_has_backup_and_integrity_guardrails() -> None:
    text = SCRIPT.read_text()

    assert "umask 077" in text
    assert "pg_dumpall" in text
    assert "gzip -t" in text
    assert "sha256sum" in text
    assert "flock" in text
    assert "AVAILABLE_BYTES" in text
    assert "REQUIRED_BYTES" in text


def test_script_installs_target_extension_before_preflight() -> None:
    text = SCRIPT.read_text()

    package_pos = text.index('postgresql-${TARGET_VERSION}-pgvector')
    check_pos = text.index("pg_upgradecluster --check")
    migrate_pos = text.index("pg_upgradecluster -v")
    assert package_pos < check_pos < migrate_pos


def test_script_keeps_old_cluster_for_rollback() -> None:
    text = SCRIPT.read_text()

    assert re.search(r"^\s*pg_dropcluster\b", text, re.MULTILINE) is None
    assert "Alter Cluster bleibt" in text
    assert "Rollback" in text


def test_script_stops_writers_and_verifies_target_port() -> None:
    text = SCRIPT.read_text()

    stop_pos = text.index("systemctl stop hydrahive2.service agentlink.service")
    migrate_pos = text.index("pg_upgradecluster -v")
    start_pos = text.index("systemctl start hydrahive2.service agentlink.service", migrate_pos)
    assert stop_pos < migrate_pos < start_pos
    assert '[ "$NEW_PORT" = "$OLD_PORT" ]' in text


def test_script_handles_collation_change_after_os_upgrade() -> None:
    text = SCRIPT.read_text()

    assert re.search(r"reindexdb .*--all", text)
    assert "REFRESH COLLATION VERSION" in text
