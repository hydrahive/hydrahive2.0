"""Schutz der Modul-Tests vor echten HydraHive-Daten.

MUSS in conftest.py vor jedem fastapi-/hydrahive-/backend-Import geladen werden:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks
        isolated_root, only_own_rows, pytest_collection_finish, pytest_configure,
        pytest_runtest_call, pytest_runtest_setup, pytest_unconfigure,
    )

Befund 26.09.2026: Eine Testsuite lief aus einer Agent-Shell mit
HH_DATA_DIR=/var/lib/hydrahive2. `settings.data_dir` ist eine cached_property;
liest ein Import den Pfad, bevor eine Fixture HH_DATA_DIR umbiegt, schreibt
und löscht die Suite im Live-System. Das hat Audit-Log, Teamchat und echte
Agents gekostet.

Drei Ebenen:
1. Beim Import zeigen HH_DATA_DIR/HH_CONFIG_DIR sofort auf ein frisches
   tmp-Verzeichnis (TEST_ROOT), noch vor dem Einsammeln.
2. Zeigt settings trotzdem auf ein echtes Verzeichnis, bricht die Suite hart
   ab (vor/nach dem Einsammeln, nach jedem Setup, nach jedem Test).
3. Gelöscht wird nur, was der Test selbst angelegt hat (`only_own_rows`,
   `only_own_files`) und nur innerhalb von TEST_ROOT (`remove_test_tree`).

Jedes Modul trägt eine identische Kopie in tests/, weil Module im Hub
eigenständig laufen. scripts/check_test_safety.py hält die Kopien gleich.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="hh-modtest-"))

# Produktions-Defaults plus alles, was beim Start in der Umgebung stand.
FORBIDDEN_DIRS = frozenset(
    Path(p).resolve() for p in (
        "/var/lib/hydrahive2", "/etc/hydrahive2", "/opt/hydrahive2",
        "/etc/samba/hh-projects.d",
        *(os.environ[k] for k in ("HH_DATA_DIR", "HH_CONFIG_DIR", "HH_BASE_DIR")
          if os.environ.get(k)),
    )
)

os.environ["HH_DATA_DIR"] = str(TEST_ROOT / "data")
os.environ["HH_CONFIG_DIR"] = str(TEST_ROOT / "config")
os.environ["HH_LOG_DIR"] = str(TEST_ROOT / "log")
os.environ["HH_SAMBA_INCLUDES_DIR"] = str(TEST_ROOT / "samba-includes")
for _sub in ("data", "config", "log", "samba-includes"):
    (TEST_ROOT / _sub).mkdir(parents=True, exist_ok=True)

_CHECKED = ("data_dir", "config_dir", "sessions_db", "agents_dir", "projects_dir",
            "workspaces_dir", "modules_dir")


def forbidden_hit(path) -> Path | None:
    """Liefert das verbotene Verzeichnis, in dem `path` liegt, sonst None."""
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError):
        return None
    for bad in FORBIDDEN_DIRS:
        if resolved == bad or bad in resolved.parents:
            return bad
    return None


def assert_isolated(when: str) -> None:
    try:
        from hydrahive.settings import settings
    except Exception:  # Core nicht importierbar: dann gibt es auch keine Live-Pfade
        return
    for attr in _CHECKED:
        try:
            value = getattr(settings, attr)
        except Exception:
            continue
        bad = forbidden_hit(value)
        if bad is not None:
            pytest.exit(
                f"ABBRUCH ({when}): settings.{attr} = {value} liegt im ECHTEN Verzeichnis "
                f"{bad}. Modul-Tests dürfen nie Live-Daten anfassen (real data dir).",
                returncode=3,
            )


# --- pytest-Hooks (conftest.py importiert sie, pytest registriert sie dort) ---

def pytest_configure(config):  # noqa: ARG001
    assert_isolated("vor dem Einsammeln")


def pytest_collection_finish(session):  # noqa: ARG001
    assert_isolated("nach dem Einsammeln")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):  # noqa: ARG001
    yield
    assert_isolated("nach dem Test-Setup")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):  # noqa: ARG001
    yield
    assert_isolated("nach dem Test")


def pytest_unconfigure(config):  # noqa: ARG001
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


# --- Nur Eigenes aufräumen ----------------------------------------------------

_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table(name: str) -> str:
    if not _TABLE.match(name):
        raise ValueError(f"ungültiger Tabellenname: {name!r}")
    return name


def refuse_real_path(path) -> None:
    """Wirft, wenn `path` nicht in TEST_ROOT liegt. Dann wird nichts gelöscht."""
    resolved = Path(path).resolve()
    root = TEST_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        bad = forbidden_hit(resolved)
        where = f"im ECHTEN Verzeichnis {bad}" if bad else f"außerhalb von {root}"
        raise RuntimeError(f"Aufräumen verweigert: {path} liegt {where}.")


@contextmanager
def isolated_root() -> Iterator[str]:
    """Liefert TEST_ROOT als Arbeitsverzeichnis der Session-Fixture.

    Ersetzt `tempfile.TemporaryDirectory()` in setup_test_env: dieselben
    Pfade, die settings schon beim Einsammeln gesehen hat. Aufgeräumt wird
    in pytest_unconfigure.
    """
    yield str(TEST_ROOT)


def remove_test_tree(path) -> None:
    """rmtree nur innerhalb von TEST_ROOT."""
    refuse_real_path(path)
    shutil.rmtree(path, ignore_errors=True)


@contextmanager
def only_own_rows(*tables: str) -> Iterator[None]:
    """Löscht nach dem Block nur Zeilen, die im Block neu dazugekommen sind.

    Merkt sich vorher pro Tabelle den höchsten rowid-Wert. Zeilen, die es
    vorher schon gab, bleiben stehen, auch wenn der Test sie geändert hat.
    """
    from hydrahive.db.connection import db
    with db() as conn:
        marks = {
            t: int(conn.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM {_table(t)}").fetchone()[0])
            for t in tables
        }
    try:
        yield
    finally:
        from hydrahive.settings import settings
        refuse_real_path(settings.sessions_db)
        with db() as conn:
            # FK-Prüfung erst beim Commit: dann ist die Tabellen-Reihenfolge egal,
            # weil am Ende alle eigenen Eltern- und Kind-Zeilen weg sind.
            conn.execute("BEGIN")
            conn.execute("PRAGMA defer_foreign_keys = ON")
            for t, marker in marks.items():
                conn.execute(f"DELETE FROM {_table(t)} WHERE rowid > ?", (marker,))


@contextmanager
def only_own_files(directory, pattern: str = "*") -> Iterator[None]:
    """Löscht nach dem Block nur Dateien in `directory`, die im Block entstanden sind."""
    directory = Path(directory)
    before = {p for p in directory.glob(pattern)} if directory.is_dir() else set()
    try:
        yield
    finally:
        if directory.is_dir():
            refuse_real_path(directory)
            for path in directory.glob(pattern):
                if path not in before and (path.is_file() or path.is_symlink()):
                    path.unlink(missing_ok=True)
