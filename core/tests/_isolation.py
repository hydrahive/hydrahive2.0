"""Isolation der Testsuite vom echten Daten-/Config-Verzeichnis.

Wird von conftest.py als ERSTES importiert — also bevor pytest auch nur eine
Testdatei einsammelt. Das ist entscheidend: `settings.data_dir` & Co. sind
cached_properties. Wertet eine Testdatei (oder eine von ihr importierte Route)
`settings.<pfad>` schon auf Modulebene aus, bleibt der erste Wert für den ganzen
Lauf hängen.

Befund 26.09.2026: In einer Agent-Shell ist HH_DATA_DIR=/var/lib/hydrahive2
gesetzt. Ein Gesamtlauf hat dort 60 Projekte, 84 Agents, 14 VMs, 7 SMB-Mounts
angelegt und project_audit_log + Teamchat-Tabellen geleert.

Deshalb: Env sofort auf ein frisches tmp-Verzeichnis umbiegen, die ursprüng-
lichen Werte als verboten merken und die Suite hart abbrechen, sobald settings
doch wieder auf ein verbotenes Verzeichnis zeigt (vor dem Einsammeln, danach,
nach jedem Test-Setup und nach jedem Testkörper).
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="hh-pytest-"))

_ISOLATED_ENV = {
    "HH_DATA_DIR": TEST_ROOT / "data",
    "HH_CONFIG_DIR": TEST_ROOT / "config",
    "HH_LOG_DIR": TEST_ROOT / "log",
    "HH_SAMBA_INCLUDES_DIR": TEST_ROOT / "samba-includes",
    "HH_SAMBA_LOG": TEST_ROOT / "log" / "hydrahive2-samba.log",
    "HH_BRIDGE_LOG": TEST_ROOT / "log" / "hydrahive2-bridge.log",
    "HH_MIGRATION_LOG": TEST_ROOT / "log" / "hydrahive2-migration.log",
}

# Produktions-Defaults + alles, was beim Start in der Umgebung stand.
FORBIDDEN_DIRS = frozenset(
    Path(p).resolve() for p in (
        "/var/lib/hydrahive2", "/etc/hydrahive2", "/opt/hydrahive2",
        "/etc/samba/hh-projects.d",
        *(os.environ[k] for k in ("HH_DATA_DIR", "HH_CONFIG_DIR", "HH_BASE_DIR")
          if os.environ.get(k)),
    )
)

_CHECKED_SETTINGS = ("data_dir", "config_dir", "sessions_db", "agents_dir", "projects_dir",
                     "workspaces_dir", "samba_includes_dir")


def isolate_env() -> None:
    """Env auf TEST_ROOT umbiegen. Muss vor jedem hydrahive-Import laufen."""
    for key, val in _ISOLATED_ENV.items():
        os.environ[key] = str(val)
    for sub in ("data", "config", "log", "samba-includes"):
        (TEST_ROOT / sub).mkdir(parents=True, exist_ok=True)


def forbidden_hit(path: Path) -> Path | None:
    """Liefert das verbotene Verzeichnis, in dem `path` liegt (oder None)."""
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError):
        return None
    for bad in FORBIDDEN_DIRS:
        if resolved == bad or bad in resolved.parents:
            return bad
    return None


def assert_isolated(when: str) -> None:
    """Bricht die gesamte Suite ab, wenn settings auf ein echtes Verzeichnis zeigt."""
    from hydrahive.settings import settings
    for attr in _CHECKED_SETTINGS:
        try:
            value = getattr(settings, attr)
        except Exception:
            continue
        bad = forbidden_hit(value)
        if bad is not None:
            pytest.exit(
                f"ABBRUCH ({when}): settings.{attr} = {value} liegt im ECHTEN Verzeichnis {bad}. "
                "Die Testsuite darf nie auf Live-Daten schreiben (real data dir).",
                returncode=3,
            )


# --- pytest-Hooks (conftest.py importiert sie, pytest findet sie dort) --------

def pytest_configure(config):  # noqa: ARG001
    assert_isolated("vor dem Einsammeln")


def pytest_collection_finish(session):  # noqa: ARG001
    # Testdateien können settings auf Modulebene ausgewertet haben.
    assert_isolated("nach dem Einsammeln")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):  # noqa: ARG001
    yield
    assert_isolated("nach dem Test-Setup")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):  # noqa: ARG001
    yield
    # Direkt nach dem Testkörper, BEVOR monkeypatch zurückgesetzt wird.
    assert_isolated("nach dem Test")


def pytest_unconfigure(config):  # noqa: ARG001
    shutil.rmtree(TEST_ROOT, ignore_errors=True)
