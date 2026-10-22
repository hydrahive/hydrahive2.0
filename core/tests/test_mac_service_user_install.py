"""install-mac.sh mit Dienst-Konto (Plan docs/plans/mac-service-user.md): Konto zuerst, Phasen mit getrennten Rollen.

HH_USER = Dienst-Konto (Besitz, Dienste, git/pip/npm), HH_BREW_USER = Mac-Besitzer (brew).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
INSTALL = INSTALLER / "install-mac.sh"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def _run(tmp_path: Path, *args: str, **extra) -> tuple[list[str], subprocess.CompletedProcess]:
    inst = tmp_path / "installer"
    log = tmp_path / "phases.log"
    for name in [p.name for p in (INSTALLER / "modules-mac").glob("*.sh")]:
        _exe(inst / "modules-mac" / name, f'echo "{name} user=$HH_USER brew=$HH_BREW_USER" >> "{log}"\n')
    for name in ("mac-admin-password.sh", "mac-addon-trigger.sh"):
        _exe(inst / "lib" / name, f'echo "{name} user=$HH_USER sudo=${{HH_TEST_SUDO:-nein}}" >> "{log}"\n')
    _exe(inst / "lib" / "mac-service-user.sh",
         f'echo "service-user svc=${{HH_SVC_USER:-_hydrahive}}" >> "{log}"\n'
         '[ -f "$HH_TEST_SVC_FAIL" ] && exit 1\necho "${HH_SVC_USER:-_hydrahive}"\n')
    (inst / "lib" / "mac-roles.sh").write_text((INSTALLER / "lib" / "mac-roles.sh").read_text())
    (inst / "install-mac.sh").write_text(INSTALL.read_text())
    bin_ = tmp_path / "ibin"
    for name, body in (("uname", "echo Darwin"), ("brew", "exit 0"), ("ipconfig", "echo 10.0.0.2"),
                       ("whoami", "echo alexmo"), ("sudo", 'HH_TEST_SUDO=ja exec "$@"'), ("chown", "exit 0")):
        _exe(bin_ / name, body + "\n")
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("HH_")}
    (tmp_path / "cfg").mkdir(exist_ok=True)
    env.update({"PATH": f"{bin_}:{os.environ['PATH']}", "HH_REPO_DIR": str(repo), "HH_CONFIG_DIR": str(tmp_path / "cfg"),
                "HH_TEST_SVC_FAIL": str(tmp_path / "svc-fail"), **extra})
    r = subprocess.run(["bash", str(inst / "install-mac.sh"), *args], env=env, capture_output=True, text=True,
                       timeout=60)
    return (log.read_text().splitlines() if log.exists() else []), r


def test_service_account_first_then_all_phases_as_service_user(tmp_path):
    phases, r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert phases[0] == "service-user svc=_hydrahive"
    rest = [p for p in phases[1:] if p.endswith(".sh user=_hydrahive brew=alexmo") or "mac-" in p]
    assert all("user=_hydrahive" in p for p in phases[1:]), phases
    assert all("brew=alexmo" in p for p in phases[1:] if p.split()[0].endswith(".sh") and "mac-" not in p), phases
    assert rest


def test_brew_user_is_the_mac_owner_not_root(tmp_path):
    phases, r = _run(tmp_path, HH_BREW_USER="root")
    assert r.returncode != 0
    assert "root" in r.stderr
    assert not any("00-deps.sh" in p for p in phases)


def test_service_account_failure_aborts(tmp_path):
    (tmp_path / "svc-fail").write_text("")
    phases, r = _run(tmp_path)
    assert r.returncode != 0
    assert not any("00-deps.sh" in p for p in phases)


def test_explicit_hh_user_owner_mode_still_possible(tmp_path):
    """Notausgang/alte Installationen: HH_USER=<Mac-Besitzer> → kein Dienst-Konto, alles wie bisher."""
    phases, r = _run(tmp_path, HH_USER="alexmo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any(p.startswith("service-user") for p in phases)
    assert all("user=alexmo" in p for p in phases), phases


def _with_fake_sudo(tmp_path: Path) -> dict:
    bin_ = tmp_path / "sbin"
    _exe(bin_ / "sudo", 'exec "$@"\n')
    _exe(bin_ / "chown", "exit 0\n")
    etc = tmp_path / "etc"
    etc.mkdir()
    return {"bin": bin_, "etc": etc}


def test_install_conf_records_service_user(tmp_path):
    """update-mac.sh erkennt umgezogene Installationen an HH_SERVICE_USER in install.conf (Etappe 3)."""
    s = _with_fake_sudo(tmp_path)
    (s["etc"] / "install.conf").write_text("HH_INSTALL_VOICE=yes\nHH_SERVICE_USER=alt\n")
    _, r = _run(tmp_path, HH_CONFIG_DIR=str(s["etc"]), PATH=f"{s['bin']}:{tmp_path / 'ibin'}:{os.environ['PATH']}")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = (s["etc"] / "install.conf").read_text().splitlines()
    assert "HH_INSTALL_VOICE=yes" in lines
    assert lines.count("HH_SERVICE_USER=_hydrahive") == 1 and "HH_SERVICE_USER=alt" not in lines


def test_owner_mode_writes_no_service_marker(tmp_path):
    s = _with_fake_sudo(tmp_path)
    _, r = _run(tmp_path, HH_USER="alexmo", HH_CONFIG_DIR=str(s["etc"]),
                PATH=f"{s['bin']}:{tmp_path / 'ibin'}:{os.environ['PATH']}")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (s["etc"] / "install.conf").exists()


def test_marker_keeps_existing_install_conf_lines(tmp_path):
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "install.conf").write_text("HH_INSTALL_VOICE=yes\n")
    phases, r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "cfg" / "install.conf").read_text().splitlines() == [
        "HH_INSTALL_VOICE=yes", "HH_SERVICE_USER=_hydrahive"]


def test_admin_password_read_via_sudo(tmp_path):
    """Die Passwort-Datei gehört dem Dienst-Konto (0600) – ohne sudo bliebe der Kasten leer."""
    phases, r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    pw = [p for p in phases if p.startswith("mac-admin-password.sh")]
    assert pw and pw[0].endswith("sudo=ja"), pw
