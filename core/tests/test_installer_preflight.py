"""Installer core-first: apt robuster + Vorab-Prüfung Netz/DNS (docs/specs/installer-core-first.md §1).

Anlass: WSL-Installation brach mitten im Herunterladen mit „Temporary failure resolving 'archive.ubuntu.com'“ ab.
Getestet mit echtem bash und PATH-Stubs (getent) gegen ein tmp-Verzeichnis – ohne root, ohne Netz.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "installer" / "lib" / "preflight.sh"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    p = bin_dir / name
    p.write_text(f"#!/usr/bin/env bash\n{body}\n")
    p.chmod(0o755)


def _run(cmd: str, tmp: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    return subprocess.run(["bash", "-c", f'set -uo pipefail; source "$1"; {cmd}', "t", str(LIB)],
                          capture_output=True, text=True,
                          env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}", "LANG": "C.UTF-8",
                               "HH_APT_CONF_DIR": str(tmp / "apt.conf.d"), "HH_PROC_VERSION": str(tmp / "version"),
                               **(env or {})})


def test_apt_retries_file_is_written_once_and_only_retries(tmp_path):
    r = _run("hh_apt_retries; hh_apt_retries", tmp_path)
    assert r.returncode == 0, r.stderr
    f = tmp_path / "apt.conf.d" / "80hydrahive-retries"
    assert f.read_text().strip().splitlines()[-1] == 'Acquire::Retries "5";'
    assert "ForceIPv4" not in f.read_text()          # kein Eingriff ins Netz


def test_existing_admin_setting_is_not_overwritten(tmp_path):
    d = tmp_path / "apt.conf.d"
    d.mkdir()
    (d / "80hydrahive-retries").write_text('Acquire::Retries "10";\n')
    _run("hh_apt_retries", tmp_path)
    assert (d / "80hydrahive-retries").read_text() == 'Acquire::Retries "10";\n'


def test_dns_ok_passes(tmp_path):
    (tmp_path / "bin").mkdir()
    _stub(tmp_path / "bin", "getent", 'echo "1.2.3.4 $2"')
    r = _run("hh_preflight_dns && echo OK", tmp_path)
    assert r.returncode == 0 and "OK" in r.stdout


def test_dns_failure_stops_with_clear_message(tmp_path):
    (tmp_path / "bin").mkdir()
    _stub(tmp_path / "bin", "getent", "exit 2")
    (tmp_path / "version").write_text("Linux version 6.8.0-45-generic (buildd@lcy02) #45-Ubuntu\n")
    r = _run("hh_preflight_dns", tmp_path)
    assert r.returncode != 0
    assert "archive.ubuntu.com" in r.stderr and "Namensauflösung" in r.stderr
    assert "wsl --shutdown" not in r.stderr          # kein WSL → kein WSL-Hinweis


def test_dns_failure_under_wsl_names_the_wsl_steps(tmp_path):
    (tmp_path / "bin").mkdir()
    _stub(tmp_path / "bin", "getent", "exit 2")
    (tmp_path / "version").write_text("Linux version 6.6.87.2-microsoft-standard-WSL2 (root@abc)\n")
    r = _run("hh_preflight_dns", tmp_path)
    assert r.returncode != 0
    assert "wsl --shutdown" in r.stderr and "dnsTunneling" in r.stderr


def test_only_first_failing_host_counts_and_all_hosts_are_checked(tmp_path):
    (tmp_path / "bin").mkdir()
    _stub(tmp_path / "bin", "getent", '[ "$2" = github.com ] && exit 2; echo "1.2.3.4 $2"')
    (tmp_path / "version").write_text("Linux\n")
    r = _run("hh_preflight_dns", tmp_path)
    assert r.returncode != 0 and "github.com" in r.stderr


def test_skip_switch_for_offline_mirrors(tmp_path):
    (tmp_path / "bin").mkdir()
    _stub(tmp_path / "bin", "getent", "exit 2")
    r = _run("hh_preflight_dns && echo OK", tmp_path, {"HH_SKIP_PREFLIGHT": "yes"})
    assert r.returncode == 0 and "OK" in r.stdout
