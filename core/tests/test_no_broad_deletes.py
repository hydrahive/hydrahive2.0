"""Tests dürfen nur löschen, was sie selbst angelegt haben.

Befund 26.09.2026: Die Suite lief gegen die echte Datenbank. Aufräum-Fixtures
mit `DELETE FROM <tabelle>` ohne WHERE haben das komplette Projekt-Audit-Log
und alle Teamchat-Identitäten gelöscht. `_cleanup_external` hat ALLE externen
Instanzen entfernt, also auch die echten Buddys von joshua22 und schmied.

Zwei Prüfungen:
1. Quelltext-Scan: Kein Test enthält ein DELETE ohne WHERE oder räumt per
   Schleife über *alle* Einträge auf (list_instances/list_all -> delete).
2. Verhalten: `only_own_rows` lässt Zeilen stehen, die es vor dem Test schon
   gab, und verweigert das Löschen in einer echten Datenbank.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO = TESTS_DIR.parent.parent
SCAN_DIRS = [TESTS_DIR, *sorted((REPO / "modules").glob("*/tests"))]

# DELETE FROM <tabelle> ohne WHERE im selben String-Literal.
_BROAD_DELETE = re.compile(r"""DELETE\s+FROM\s+[A-Za-z_{][A-Za-z0-9_.{}\[\]]*\s*["')]""", re.I)
# Schleife über ALLE Einträge mit Löschen im Rumpf.
_LIST_ALL = re.compile(
    r"for\s+\w+\s+in\s+[\w.]*\b(list_instances|list_all|list_users|list_keys|list_projects)\(\s*\)\s*:"
)
_DELETE_CALL = re.compile(r"\.(delete|delete_instance|remove|rmtree)\(|rmtree\(")


def _py_files() -> list[Path]:
    files = []
    for d in SCAN_DIRS:
        files += [p for p in d.rglob("*.py") if "__pycache__" not in p.parts]
    return files


def test_no_delete_without_where_in_tests() -> None:
    offenders = []
    for path in _py_files():
        if path.name == Path(__file__).name:
            continue
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _BROAD_DELETE.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{no}: {line.strip()}")
    assert not offenders, (
        "Tests dürfen keine ganzen Tabellen leeren (DELETE ohne WHERE). "
        "Stattdessen tests._own_rows.only_own_rows(...) verwenden:\n" + "\n".join(offenders)
    )


def test_no_cleanup_loop_over_all_entries() -> None:
    offenders = []
    for path in _py_files():
        if path.name == Path(__file__).name:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not _LIST_ALL.search(line):
                continue
            indent = len(line) - len(line.lstrip())
            for body in lines[i + 1:]:
                if body.strip() and len(body) - len(body.lstrip()) <= indent:
                    break
                if _DELETE_CALL.search(body):
                    offenders.append(f"{path.relative_to(REPO)}:{i + 1}: {line.strip()}")
                    break
    assert not offenders, (
        "Tests dürfen nicht über ALLE Einträge laufen und löschen. "
        "Nur die im Test angelegten IDs merken und löschen:\n" + "\n".join(offenders)
    )


_HELPER_IMPORT = re.compile(r"^\s*from\s+_hh_isolation\s+import\b")
_RISKY_IMPORT = re.compile(r"^\s*(from|import)\s+(fastapi|hydrahive|backend)\b")


@pytest.mark.parametrize("tests_dir", sorted((REPO / "modules").glob("*/tests")), ids=lambda p: p.parent.name)
def test_bundled_module_suite_is_isolated(tests_dir: Path) -> None:
    """Gebündelte Module laden _hh_isolation vor jedem hydrahive-Import.

    Die Modul-conftests laufen eigenständig (ohne core/tests/conftest.py) und
    haben HH_DATA_DIR früher erst in einer Session-Fixture umgebogen. Zu spät,
    wenn schon beim Einsammeln etwas settings liest.
    """
    conftest = tests_dir / "conftest.py"
    helper = tests_dir / "_hh_isolation.py"
    assert helper.is_file(), f"{helper.relative_to(REPO)} fehlt"
    lines = conftest.read_text(encoding="utf-8").splitlines()
    helper_at = next((i for i, line in enumerate(lines) if _HELPER_IMPORT.search(line)), None)
    risky_at = next((i for i, line in enumerate(lines) if _RISKY_IMPORT.search(line)), None)
    assert helper_at is not None, f"{conftest.relative_to(REPO)} lädt _hh_isolation nicht"
    assert risky_at is None or helper_at < risky_at, (
        f"{conftest.relative_to(REPO)}:{risky_at + 1}: Import vor _hh_isolation"
    )


def test_only_own_rows_keeps_preexisting_rows(setup_test_env) -> None:
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.projects import audit
    from tests._own_rows import only_own_rows

    init_db()
    audit.log("p-vorher", "till", "project_updated")
    with db() as conn:
        before = conn.execute("SELECT COUNT(*) FROM project_audit_log").fetchone()[0]

    with only_own_rows("project_audit_log"):
        audit.log("p-test", "till", "member_added")
        audit.log("p-test", "till", "member_added")

    with db() as conn:
        after = conn.execute("SELECT COUNT(*) FROM project_audit_log").fetchone()[0]
        kept = conn.execute(
            "SELECT COUNT(*) FROM project_audit_log WHERE project_id = 'p-vorher'"
        ).fetchone()[0]
        own = conn.execute(
            "SELECT COUNT(*) FROM project_audit_log WHERE project_id = 'p-test'"
        ).fetchone()[0]
        conn.execute("DELETE FROM project_audit_log WHERE project_id = 'p-vorher'")
    assert after == before, "nur die im Test angelegten Zeilen dürfen weg sein"
    assert kept == 1 and own == 0


def test_only_own_rows_refuses_real_database(monkeypatch, tmp_path) -> None:
    """Zeigt die DB auf ein echtes Verzeichnis, wird nichts gelöscht."""
    from tests import _isolation
    from tests._own_rows import refuse_real_db

    fake_real = tmp_path / "echt"
    fake_real.mkdir()
    monkeypatch.setattr(_isolation, "FORBIDDEN_DIRS", frozenset({fake_real.resolve()}))
    with pytest.raises(RuntimeError, match="ECHTEN"):
        refuse_real_db(fake_real / "sessions.db")
    refuse_real_db(tmp_path / "anders" / "sessions.db")  # außerhalb: erlaubt


def test_scanner_detects_broad_delete_in_sample(tmp_path) -> None:
    """Gegenprobe: Der Scanner erkennt die Muster vom 26.09. wirklich."""
    samples = [
        'conn.execute("DELETE FROM project_audit_log")',
        "c.execute('DELETE FROM module_tasks')",
        'conn.execute(f"DELETE FROM {spec.table}")',
    ]
    for s in samples:
        assert _BROAD_DELETE.search(s), s
    for ok in ('conn.execute("DELETE FROM t WHERE id = ?", (1,))',
               'conn.execute(f"DELETE FROM {table} WHERE rowid > ?", (m,))'):
        assert not _BROAD_DELETE.search(ok), ok
    loop = "for inst in ei.list_instances():\n    ei.delete_instance(inst['agent_id'])"
    assert _LIST_ALL.search(loop.splitlines()[0])
