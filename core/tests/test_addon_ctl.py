"""installer/addon-ctl.sh wirklich ausführen (Spec installer-core-first §3).

Das Repo liegt als Kopie der echten Bibliothek plus Ersatz-Modul-Skripte in tmp_path. Die Ersatz-Skripte schreiben
ihren Aufruf (Name + HH_INSTALL_*-Wert) mit und enden mit dem Exit-Code aus FAIL_<NAME>. So wird das echte Verhalten
des Runners geprüft: Positivliste, install.conf nur bei Erfolg, Abhängigkeit voice → containers, Trigger am Ende weg.
"""
from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
CTL = INSTALLER / "addon-ctl.sh"

SCRIPTS = {
    "containers": "70-containers.sh", "vms": "65-vms.sh", "samba": "47-samba.sh",
    "whatsapp": "45-whatsapp.sh", "voice": "55-voice.sh", "tailscale": "80-tailscale.sh",
}

FAKE_MODULE = """#!/usr/bin/env bash
name="$(basename "$0" .sh)"
printf '%s %s\\n' "$name" "$(env | grep '^HH_INSTALL_' | sort | tr '\\n' ' ')" >> "$FAKE_LOG"
var="FAIL_${name//-/_}"
exit "${!var:-0}"
"""


def _exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def box(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    (repo / "installer" / "modules").mkdir(parents=True)
    (repo / "installer" / "lib").mkdir()
    shutil.copy(INSTALLER / "lib" / "install-choices.sh", repo / "installer" / "lib")
    for script in SCRIPTS.values():
        _exe(repo / "installer" / "modules" / script, FAKE_MODULE)
    data, conf = tmp_path / "data", tmp_path / "etc"
    data.mkdir()
    conf.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    return {"repo": repo, "data": data, "conf": conf, "bin": bin_dir, "log": tmp_path / "calls.log",
            "trigger": data / ".addon_request", "install_conf": conf / "install.conf"}


def _run(box: dict, request: str | None, **env: str) -> subprocess.CompletedProcess[str]:
    if request is not None:
        box["trigger"].write_text(request)
    full_env = {
        "PATH": f"{box['bin']}:/usr/bin:/bin", "HH_REPO_DIR": str(box["repo"]), "HH_DATA_DIR": str(box["data"]),
        "HH_CONFIG_DIR": str(box["conf"]), "FAKE_LOG": str(box["log"]),
        "HH_INCUS_BIN": str(box["bin"] / "kein-incus"),     # Host kann echtes incus haben – Standard: fehlt
        **env,
    }
    return subprocess.run(["bash", str(CTL)], env=full_env, capture_output=True, text=True, timeout=30)


def _calls(box: dict) -> list[str]:
    return box["log"].read_text().splitlines() if box["log"].exists() else []


@pytest.mark.parametrize("addon", sorted(SCRIPTS))
def test_each_allowed_addon_runs_its_script_and_is_recorded(box, addon):
    env = {}
    if addon == "voice":
        _exe(box["bin"] / "incus", "#!/bin/sh\nexit 0\n")          # Container schon da → kein Nachziehen
        env["HH_INCUS_BIN"] = str(box["bin"] / "incus")
    r = _run(box, f"install {addon}\n", **env)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(box)
    assert len(calls) == 1 and calls[0].startswith(SCRIPTS[addon].removesuffix(".sh"))
    var = f"HH_INSTALL_{addon.upper()}"
    assert f"{var}=yes" in calls[0]
    assert f"{var}='yes'" in box["install_conf"].read_text()
    assert f"[hh2-addon] FERTIG: install {addon} ok" in r.stdout
    assert not box["trigger"].exists()


def test_failure_keeps_install_conf_untouched(box):
    box["install_conf"].write_text("HH_INSTALL_SAMBA='no'\n")
    r = _run(box, "install samba", FAIL_47_samba="3")
    assert r.returncode != 0
    assert box["install_conf"].read_text() == "HH_INSTALL_SAMBA='no'\n"
    assert "[hh2-addon] FEHLER: install samba fehlgeschlagen" in r.stdout
    assert not box["trigger"].exists()


@pytest.mark.parametrize("request_text", [
    "install postgres", "install local_media", "uninstall samba", "install", "", "install samba; rm -rf /",
    "install ../../bin/sh", "install SAMBA", "install samba extra", "install samba\ninstall vms",
])
def test_anything_outside_the_list_is_rejected(box, request_text):
    r = _run(box, request_text)
    assert r.returncode == 2
    assert _calls(box) == []
    assert not box["install_conf"].exists()
    assert "[hh2-addon] FEHLER: unbekannte Anfrage verworfen" in r.stdout
    assert not box["trigger"].exists()


def test_voice_pulls_in_containers_first_when_incus_missing(box):
    r = _run(box, "install voice")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c.split()[0] for c in _calls(box)] == ["70-containers", "55-voice"]
    conf = box["install_conf"].read_text()
    assert "HH_INSTALL_CONTAINERS='yes'" in conf and "HH_INSTALL_VOICE='yes'" in conf


def test_voice_stops_when_containers_fail(box):
    r = _run(box, "install voice", FAIL_70_containers="1")
    assert r.returncode != 0
    assert [c.split()[0] for c in _calls(box)] == ["70-containers"]
    assert not box["install_conf"].exists()


def test_no_request_does_nothing(box):
    r = _run(box, None)
    assert r.returncode == 0
    assert _calls(box) == [] and r.stdout == ""


def test_log_starts_with_a_header_line(box):
    r = _run(box, "install whatsapp")
    assert r.stdout.splitlines()[0].startswith("[hh2-addon] ===== ")
    assert "install whatsapp" in r.stdout.splitlines()[0]
