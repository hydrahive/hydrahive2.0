"""Die Testsuite darf NIE in das echte Daten-/Config-Verzeichnis schreiben.

Befund 26.09.2026: Ein Gesamtlauf aus einer Agent-Shell (dort ist
HH_DATA_DIR=/var/lib/hydrahive2 gesetzt) hat im Live-System 60 Projekte,
84 Agents, 14 VMs, 7 SMB-Mounts u.a. angelegt und das komplette
project_audit_log sowie die Teamchat-Tabellen geleert. Auslöser: Eine
Testdatei importierte auf Modulebene eine Route, die `settings.<pfad>`
auswertet. Das geschah beim Einsammeln, BEVOR die session-Fixture
`setup_test_env` HH_DATA_DIR auf ein tmp-Verzeichnis umbog. Weil
`settings.data_dir` eine cached_property ist, blieb der echte Pfad hängen.

Die Tests hier starten pytest als Unterprozess mit genau so einer Umgebung
(HH_DATA_DIR/HH_CONFIG_DIR zeigen auf ein Fake-Prod-Verzeichnis) und nutzen
dabei die echte conftest.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent


def _run_inner(tmp_path: Path, body: str) -> tuple[subprocess.CompletedProcess, Path, Path]:
    fake_data = tmp_path / "fake-prod-data"
    fake_cfg = tmp_path / "fake-prod-config"
    fake_data.mkdir()
    fake_cfg.mkdir()
    # Gleiche Struktur wie core/: <root>/tests/ als Paket mit echter conftest.py.
    inner = tmp_path / "inner"
    pkg = inner / "tests"
    pkg.mkdir(parents=True)
    for name in ("__init__.py", "conftest.py", "_isolation.py"):
        (pkg / name).write_text((CORE / "tests" / name).read_text())
    (pkg / "test_inner.py").write_text(textwrap.dedent(body))
    env = {
        **os.environ,
        "HH_DATA_DIR": str(fake_data),
        "HH_CONFIG_DIR": str(fake_cfg),
        "PYTHONPATH": str(CORE / "src"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_inner.py", "-q", "-p", "no:cacheprovider",
         "--rootdir", str(inner), "-c", os.devnull],
        cwd=inner, env=env, capture_output=True, text=True, timeout=180,
    )
    return proc, fake_data, fake_cfg


def _leaked(d: Path) -> list[str]:
    return sorted(str(p.relative_to(d)) for p in d.rglob("*"))


def test_collection_time_settings_access_never_hits_real_dirs(tmp_path: Path) -> None:
    """settings.* beim Einsammeln (Modulebene) darf nicht auf das echte Verzeichnis zeigen."""
    proc, fake_data, fake_cfg = _run_inner(tmp_path, """
        from hydrahive.settings import settings

        # Modulebene, genau wie der Auslöser vom 26.09.:
        DATA_AT_IMPORT = settings.data_dir
        PROJECTS_AT_IMPORT = settings.projects_dir

        def test_writes_like_the_suite_does():
            p = settings.projects_dir / "leak-probe"
            p.mkdir(parents=True, exist_ok=True)
            (p / "config.json").write_text("{}")
            (settings.config_dir / "probe.json").write_text("{}")
    """)
    out = proc.stdout + proc.stderr
    assert _leaked(fake_data) == [], f"Test hat ins echte data_dir geschrieben: {_leaked(fake_data)}\n{out}"
    assert _leaked(fake_cfg) == [], f"Test hat ins echte config_dir geschrieben: {_leaked(fake_cfg)}\n{out}"
    assert proc.returncode == 0, out


def test_real_env_dirs_are_never_used_even_without_module_import(tmp_path: Path) -> None:
    """Auch der normale Weg (settings erst im Test) darf das echte Verzeichnis nicht anfassen."""
    proc, fake_data, fake_cfg = _run_inner(tmp_path, """
        def test_uses_settings_late():
            from hydrahive.settings import settings
            settings.ensure_dirs()
            (settings.agents_dir / "probe").mkdir(parents=True, exist_ok=True)
    """)
    out = proc.stdout + proc.stderr
    assert _leaked(fake_data) == [] and _leaked(fake_cfg) == [], out
    assert proc.returncode == 0, out


def test_guard_aborts_when_settings_point_back_to_real_dir(tmp_path: Path) -> None:
    """Biegt ein Test settings.data_dir aufs echte Verzeichnis zurück, muss der Guard abbrechen."""
    fake = tmp_path / "fake-prod-data"
    proc, fake_data, _ = _run_inner(tmp_path, f"""
        from pathlib import Path
        from hydrahive.settings import settings

        def test_sneaks_real_path_back(monkeypatch):
            monkeypatch.setattr(settings, "data_dir", Path({str(fake)!r}), raising=False)
            (settings.data_dir / "should-not-exist").mkdir()
    """)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, "Guard hat nicht angeschlagen:\n" + out
    assert "ECHTE" in out or "real" in out.lower(), out
