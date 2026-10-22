"""Mac-Container: Einbindung in Installer, Update, Backend-plist und Cockpit-Runner (docs/plans/mac-containers.md §3).

Standard AUS (Till 21.10.2026: „ja als Option“). Linux-Installer bleibt unberührt.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
INSTALL = INSTALLER / "install-mac.sh"
UPDATE = INSTALLER / "update-mac.sh"
LAUNCHD = INSTALLER / "modules-mac" / "50-launchd.sh"
RUNNER = INSTALLER / "lib" / "mac-addon-ctl.sh"
TRIGGER = INSTALLER / "lib" / "mac-addon-trigger.sh"


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


# --- install-mac.sh: Phase nur auf Wunsch --------------------------------------------------------------------

def _run_install(tmp_path: Path, *args: str, **extra) -> list[str]:
    inst = tmp_path / "installer"
    log = tmp_path / "phases.log"
    for d in ("modules-mac", "lib"):
        (inst / d).mkdir(parents=True, exist_ok=True)
    for name in [p.name for p in (INSTALLER / "modules-mac").glob("*.sh")]:
        _exe(inst / "modules-mac" / name, f'echo "{name}" >> "{log}"\n')
    for name in ("mac-admin-password.sh", "mac-addon-trigger.sh"):
        _exe(inst / "lib" / name, f'echo "{name}" >> "{log}"\n')
    (inst / "install-mac.sh").write_text(INSTALL.read_text())
    bin_ = tmp_path / "ibin"
    for name, body in (("uname", "echo Darwin"), ("brew", "exit 0"), ("ipconfig", "echo 10.0.0.2")):
        _exe(bin_ / name, body + "\n")
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_REPO_DIR": str(repo), **extra}
    env.pop("HH_INSTALL_CONTAINERS", None) if "HH_INSTALL_CONTAINERS" not in extra else None
    r = subprocess.run(["bash", str(inst / "install-mac.sh"), *args], env=env, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return log.read_text().splitlines()


def test_install_without_option_skips_containers(tmp_path):
    phases = _run_install(tmp_path)
    assert "70-containers.sh" not in phases
    assert "mac-addon-trigger.sh" in phases                  # Nachinstallieren im Cockpit möglich


def test_install_with_option_runs_containers_then_relaunchd(tmp_path):
    phases = _run_install(tmp_path, "--with=containers")
    i = phases.index("70-containers.sh")
    assert phases[i + 1] == "50-launchd.sh"                    # Backend-PATH neu mit incus
    assert phases.index("48-postgres.sh") < i < phases.index("60-nginx.sh")


def test_install_env_option(tmp_path):
    assert "70-containers.sh" in _run_install(tmp_path, HH_INSTALL_CONTAINERS="yes")


# --- 50-launchd.sh: PATH mit Container-Werkzeugen ------------------------------------------------------------

def _launchd(tmp_path: Path, ct_bin: Path | None) -> dict:
    bin_ = tmp_path / "lbin"
    _exe(bin_ / "sudo", '"$@"\n')
    _exe(bin_ / "launchctl", 'case "$1" in list) echo "1 0 io.hydrahive.backend";; esac\n')
    _exe(bin_ / "brew", "echo /usr/local\n")
    cfg = tmp_path / "etc"
    cfg.mkdir(exist_ok=True)
    plist = tmp_path / "backend.plist"
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_CONFIG_DIR": str(cfg),
           "HH_DATA_DIR": str(tmp_path / "data"), "HH_REPO_DIR": "/opt/hydrahive2", "HH_USER": "tester",
           "HH_HOST": "127.0.0.1", "HH_PORT": "8001", "HH_BACKEND_PLIST": str(plist),
           "HH_CT_BIN": str(ct_bin or tmp_path / "fehlt")}
    r = subprocess.run(["bash", str(LAUNCHD)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return plistlib.loads(plist.read_bytes())["EnvironmentVariables"]


def test_backend_path_contains_container_tools_when_installed(tmp_path):
    ct = tmp_path / "ctbin"
    ct.mkdir()
    env = _launchd(tmp_path, ct)
    assert env["PATH"].split(":")[1] == str(ct)               # direkt nach dem venv
    assert env["COLIMA_HOME"] == str(tmp_path / "data" / "colima")


def test_backend_path_without_container_tools(tmp_path):
    env = _launchd(tmp_path, None)
    assert "containers/bin" not in env["PATH"] and "fehlt" not in env["PATH"]


# --- update-mac.sh -----------------------------------------------------------------------------------------------

def test_update_keeps_wanted_containers_and_trigger():
    text = UPDATE.read_text()
    assert "mac-addon-trigger.sh" in text
    i = text.index("modules-mac/70-containers.sh")
    block = text[i - 600:i + 300]
    assert "HH_INSTALL_CONTAINERS=yes" in block               # nur wenn gewünscht
    assert "FEHLGESCHLAGEN" in block and "exit 1" not in block
    assert "/usr/local/lib/hydrahive2/containers/bin" in text  # plist neu, wenn PATH fehlt


# --- Cockpit-Runner -------------------------------------------------------------------------------------------------

@pytest.fixture
def runner(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    log = tmp_path / "ran.log"
    _exe(repo / "installer" / "modules-mac" / "70-containers.sh",
         f'echo "70 user=$HH_USER" >> "{log}"\n[ -f "{tmp_path}/fail70" ] && exit 1; exit 0\n')
    _exe(repo / "installer" / "modules-mac" / "80-tailscale.sh", f'echo "80 user=$HH_USER" >> "{log}"\n')
    _exe(repo / "installer" / "modules-mac" / "50-launchd.sh", f'echo "50" >> "{log}"\n')
    data = tmp_path / "data"
    data.mkdir()
    return {"tmp": tmp_path, "repo": repo, "log": log, "data": data, "req": data / ".addon_request"}


def _run_runner(r: dict) -> subprocess.CompletedProcess:
    env = {**os.environ, "HH_REPO_DIR": str(r["repo"]), "HH_DATA_DIR": str(r["data"]), "HH_USER": "tester",
           "HH_CONFIG_DIR": str(r["tmp"] / "etc")}
    return subprocess.run(["bash", str(RUNNER)], env=env, capture_output=True, text=True, timeout=60)


def test_runner_installs_containers_and_restarts_backend(runner):
    runner["req"].write_text("install containers\n")
    res = _run_runner(runner)
    assert res.returncode == 0, res.stdout + res.stderr
    assert runner["log"].read_text().splitlines() == ["70 user=tester", "50"]
    assert "[hh2-addon] FERTIG: install containers ok" in res.stdout
    assert not runner["req"].exists()                           # Anfrage weg → API meldet „fertig“


def test_runner_installs_tailscale(runner):
    runner["req"].write_text("install tailscale\n")
    res = _run_runner(runner)
    assert res.returncode == 0, res.stdout + res.stderr
    assert runner["log"].read_text().splitlines() == ["80 user=tester", "50"]
    assert "[hh2-addon] FERTIG: install tailscale ok" in res.stdout


@pytest.mark.parametrize("req", ["install samba\n", "install vms\n", "install containers; rm -rf /\n", "x\n",
                                 "install tailscale ../x\n", "install whatsapp\n", "install voice; id\n"])
def test_runner_refuses_everything_else(runner, req):
    runner["req"].write_text(req)
    res = _run_runner(runner)
    assert res.returncode == 2
    assert not runner["log"].exists()
    assert "[hh2-addon] FEHLER:" in res.stdout
    assert not runner["req"].exists()


def test_runner_failure_reported_like_linux(runner):
    runner["req"].write_text("install containers\n")
    (runner["tmp"] / "fail70").write_text("")
    res = _run_runner(runner)
    assert res.returncode == 1
    assert "[hh2-addon] FEHLER: install containers fehlgeschlagen" in res.stdout
    assert runner["log"].read_text().splitlines() == ["70 user=tester"]   # kein Backend-Neustart


def test_runner_without_request_does_nothing(runner):
    res = _run_runner(runner)
    assert res.returncode == 0 and res.stdout == ""


def test_trigger_plist_watches_request(tmp_path):
    bin_ = tmp_path / "tbin"
    _exe(bin_ / "sudo", '"$@"\n')
    _exe(bin_ / "launchctl", f'echo "launchctl $*" >> "{tmp_path}/calls"\n')
    plist = tmp_path / "addon.plist"
    (tmp_path / "log").mkdir()
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_USER": "tester",
           "HH_DATA_DIR": str(tmp_path / "data"), "HH_ADDON_PLIST": str(plist), "HH_LOG_DIR": str(tmp_path / "log")}
    r = subprocess.run(["bash", str(TRIGGER)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    p = plistlib.loads(plist.read_bytes())
    assert p["Label"] == "io.hydrahive.addon"
    assert p["WatchPaths"] == [str(tmp_path / "data" / ".addon_request")]
    assert p["ProgramArguments"][1].endswith("installer/lib/mac-addon-ctl.sh")
    assert "UserName" not in p                                   # root (installiert Dienste)
    assert p["StandardOutPath"] == str(tmp_path / "log" / "hydrahive2-addon.log")


def test_backend_log_dir_matches_runner_log():
    """Das Cockpit liest settings.log_dir/hydrahive2-addon.log; die Mac-plist setzt HH_LOG_DIR=/usr/local/var/log."""
    assert "/usr/local/var/log" in LAUNCHD.read_text()
    assert 'HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"' in TRIGGER.read_text()



def test_install_tailscale_option(tmp_path):
    phases = _run_install(tmp_path, "--with=containers,tailscale")
    assert "70-containers.sh" in phases
    i = phases.index("80-tailscale.sh")
    assert phases[i + 1] == "50-launchd.sh"
    assert i < phases.index("60-nginx.sh")
    assert "80-tailscale.sh" not in _run_install(tmp_path / "b")             # Standard aus


def test_backend_path_contains_tailscale_when_installed(tmp_path):
    ts = tmp_path / "tsbin"
    ts.mkdir()
    bin_ = tmp_path / "lbin"
    _exe(bin_ / "sudo", '"$@"\n')
    _exe(bin_ / "launchctl", 'case "$1" in list) echo "1 0 io.hydrahive.backend";; esac\n')
    _exe(bin_ / "brew", "echo /usr/local\n")
    (tmp_path / "etc").mkdir()
    plist = tmp_path / "backend.plist"
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_CONFIG_DIR": str(tmp_path / "etc"),
           "HH_DATA_DIR": str(tmp_path / "data"), "HH_REPO_DIR": "/opt/hydrahive2", "HH_USER": "tester",
           "HH_HOST": "127.0.0.1", "HH_PORT": "8001", "HH_BACKEND_PLIST": str(plist),
           "HH_CT_BIN": str(tmp_path / "fehlt"), "HH_TS_BIN": str(ts)}
    r = subprocess.run(["bash", str(LAUNCHD)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    path = plistlib.loads(plist.read_bytes())["EnvironmentVariables"]["PATH"].split(":")
    assert path[1] == str(ts)


def test_update_keeps_wanted_tailscale():
    text = UPDATE.read_text()
    i = text.index("modules-mac/80-tailscale.sh")
    block = text[i - 400:i + 300]
    assert "HH_INSTALL_TAILSCALE=yes" in block and "FEHLGESCHLAGEN" in block and "exit 1" not in block
    assert "/usr/local/lib/hydrahive2/tailscale/bin" in text
