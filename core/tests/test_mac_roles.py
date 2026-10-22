"""macOS-Installer: zwei Rollen – Homebrew-Besitzer und Dienst-Konto (docs/plans/mac-service-user.md).

installer/lib/mac-roles.sh stellt as_brew/as_svc/priv/hh_svc_home bereit. Läuft der Aufrufer schon als die
gewünschte Rolle, wird direkt ausgeführt (alter Weg: Dienst-Nutzer = Mac-Besitzer, nichts ändert sich);
sonst über sudo -u. Homebrew-Besitzer ohne Angabe = Besitzer der brew-Datei (Update als root braucht keine
Einstellung).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROLES = Path(__file__).resolve().parents[2] / "installer" / "lib" / "mac-roles.sh"
ME = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    calls = tmp_path / "calls.log"
    (bin_ / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{calls}"\n[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (bin_ / "dscl").write_text('#!/bin/bash\necho "NFSHomeDirectory: /usr/local/var/hydrahive2/home"\n')
    brew = tmp_path / "brew"
    brew.write_text(f'#!/bin/bash\necho "brew-als $(id -un) $*" >> "{calls}"\n')
    for f in (*bin_.iterdir(), brew):
        f.chmod(0o755)
    return bin_, calls


def _run(tmp_path: Path, script: str, **env) -> tuple[subprocess.CompletedProcess, str]:
    bin_, calls = _setup(tmp_path)
    full = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_BREW": str(tmp_path / "brew"), **env}
    r = subprocess.run(["bash", "-c", f'set -euo pipefail\nsource "{ROLES}"\n{script}'], env=full,
                       capture_output=True, text=True, timeout=30)
    return r, calls.read_text() if calls.exists() else ""


def test_as_svc_direct_when_already_service_user(tmp_path):
    r, calls = _run(tmp_path, "as_svc true", HH_USER=ME)
    assert r.returncode == 0, r.stderr
    assert "sudo" not in calls


def test_as_svc_via_sudo_with_home_and_path(tmp_path):
    r, calls = _run(tmp_path, "as_svc true", HH_USER="_hydrahive")
    assert r.returncode == 0, r.stderr
    line = calls.splitlines()[0]
    assert line.startswith("sudo -u _hydrahive env PATH=")
    assert "HOME=/usr/local/var/hydrahive2/home" in line
    assert line.endswith(" true")


def test_as_brew_direct_when_brew_user(tmp_path):
    r, calls = _run(tmp_path, "as_brew --prefix", HH_USER="_hydrahive", HH_BREW_USER=ME)
    assert r.returncode == 0, r.stderr
    assert calls.strip() == f"brew-als {ME} --prefix"


def test_as_brew_via_sudo_as_brew_user_never_service_account(tmp_path):
    r, calls = _run(tmp_path, "as_brew list nginx", HH_USER="_hydrahive", HH_BREW_USER="alexmo")
    assert r.returncode == 0, r.stderr
    assert calls.splitlines()[0] == f"sudo -u alexmo {tmp_path / 'brew'} list nginx"


def test_brew_user_defaults_to_owner_of_brew(tmp_path):
    """Update als root: kein HH_BREW_USER gesetzt → Besitzer der brew-Datei (= Mac-Besitzer)."""
    r, _ = _run(tmp_path, 'echo "$HH_BREW_USER"', HH_USER="_hydrahive")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ME


def test_brew_user_old_way_is_hh_user(tmp_path):
    """Alter Weg (kein System-Konto): brew wie bisher als HH_USER – nichts ändert sich."""
    r, _ = _run(tmp_path, 'echo "$HH_BREW_USER"', HH_USER="admin")
    assert r.stdout.strip() == "admin"


def test_svc_home_falls_back_to_users_dir(tmp_path):
    r, _ = _run(tmp_path, 'dscl() { return 1; }\nhh_svc_home', HH_USER="bob")
    assert r.stdout.strip() == "/Users/bob"


def test_is_service_account(tmp_path):
    r, _ = _run(tmp_path, 'hh_service_account && echo ja || echo nein', HH_USER="_hydrahive", HH_BREW_USER="alexmo")
    assert r.stdout.strip() == "ja"
    r, _ = _run(tmp_path, 'hh_service_account && echo ja || echo nein', HH_USER="alexmo", HH_BREW_USER="alexmo")
    assert r.stdout.strip() == "nein"


def test_conf_set_reads_via_sudo_and_keeps_other_lines(tmp_path):
    """install.conf liegt im Config-Ordner des Dienst-Kontos – der Mac-Besitzer liest nur über sudo.
    Ohne sudo hielt er die Datei für leer und überschrieb die übrigen Merker."""
    cfg = tmp_path / "etc"
    cfg.mkdir()
    (cfg / "install.conf").write_text("HH_SERVICE_USER=_hydrahive\nHH_INSTALL_VOICE=no\n")
    (tmp_path / "bin").mkdir(exist_ok=True)
    _exe = tmp_path / "bin" / "chown"
    _exe.write_text("#!/bin/bash\nexit 0\n")
    _exe.chmod(0o755)
    r, calls = _run(tmp_path, f'hh_conf_set "{cfg}/install.conf" HH_INSTALL_VOICE yes', HH_USER="_hydrahive",
                    HH_BREW_USER=ME)
    assert r.returncode == 0, r.stderr
    assert (cfg / "install.conf").read_text().splitlines() == ["HH_SERVICE_USER=_hydrahive", "HH_INSTALL_VOICE=yes"]
    assert f"sudo cat {cfg}/install.conf" in calls
    assert f"sudo chown _hydrahive {cfg}/install.conf" in calls


def test_conf_get(tmp_path):
    cfg = tmp_path / "install.conf"
    cfg.write_text("HH_INSTALL_VOICE=yes\n")
    r, calls = _run(tmp_path, f'hh_conf_get "{cfg}" HH_INSTALL_VOICE; hh_conf_get "{cfg}" FEHLT || echo leer',
                    HH_USER="_hydrahive", HH_BREW_USER=ME)
    assert r.stdout.split() == ["yes", "leer"]
    assert f"sudo cat {cfg}" in calls
