"""macOS: Rückweg nach abgebrochenem Umzug auf das Dienst-Konto (lib/mac-migrate-rollback.sh, Etappe 3).

Befund 22.10.2026 (.186): Abbruch beim Datenbank-Import ließ einen halben Umzug zurück – nichts lief. Rückweg: neue
Dienste anhalten, Besitz zurück an den alten Nutzer, plists aus der Sicherung zurück, alte Dienste starten.
Das Konto bleibt (schadet nicht, nächstes Update nutzt es wieder); der neue Datenbank-Ordner bleibt liegen.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
ROLLBACK = INSTALLER / "lib" / "mac-migrate-rollback.sh"


def _exe(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/bash\n" + body)
    p.chmod(0o755)


@pytest.fixture
def rb(tmp_path: Path) -> dict:
    bin_, calls = tmp_path / "bin", tmp_path / "calls.log"
    calls.write_text("")
    rec = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    for name in ("chown", "launchctl"):
        _exe(bin_ / name, rec)
    backup = tmp_path / "backup"
    (backup / "plists").mkdir(parents=True)
    for label in ("backend", "postgres", "colima"):
        (backup / "plists" / f"io.hydrahive.{label}.plist").write_text(f"alt-{label}")
    plists = tmp_path / "LaunchDaemons"
    plists.mkdir()
    for label in ("backend", "postgres", "colima", "update"):
        (plists / f"io.hydrahive.{label}.plist").write_text(f"neu-{label}")
    dirs = {name: tmp_path / name for name in ("repo", "data", "etc", "hl", "hlcfg", "log")}
    for d in dirs.values():
        d.mkdir()
    (dirs["log"] / "hydrahive2.log").write_text("")
    (dirs["data"] / "tailscale").mkdir()
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "HH_OLD_USER": "admin", "HH_SVC_USER": "_hydrahive",
           "HH_BACKUP": str(backup), "HH_PLIST_DIR": str(plists), "HH_REPO_DIR": str(dirs["repo"]),
           "HH_DATA_DIR": str(dirs["data"]), "HH_CONFIG_DIR": str(dirs["etc"]), "HH_HL_DIR": str(dirs["hl"]),
           "HH_HL_CONFIG_DIR": str(dirs["hlcfg"]), "HH_LOG_DIR": str(dirs["log"])}
    return {"tmp": tmp_path, "env": env, "calls": calls, "plists": plists, "dirs": dirs}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(ROLLBACK)], env={**m["env"], **extra}, capture_output=True, text=True, timeout=30)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def test_stops_new_services_first(rb):
    r = _run(rb)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(rb)
    i_stop = calls.index("launchctl bootout system/io.hydrahive.postgres")
    i_chown = next(i for i, c in enumerate(calls) if c.startswith("chown -R admin"))
    assert i_stop < i_chown


def test_ownership_back_to_old_user(rb):
    r = _run(rb)
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("repo", "data", "etc", "hl", "hlcfg"):
        assert f"chown -R admin {rb['dirs'][name]}" in _calls(rb), name
    assert f"chown -R root {rb['dirs']['data']}/tailscale" in _calls(rb)
    assert f"chown admin {rb['dirs']['log']}/hydrahive2.log" in _calls(rb)


def test_plists_restored_and_services_started(rb):
    r = _run(rb)
    assert r.returncode == 0, r.stdout + r.stderr
    for label in ("backend", "postgres", "colima"):
        assert (rb["plists"] / f"io.hydrahive.{label}.plist").read_text() == f"alt-{label}"
    assert (rb["plists"] / "io.hydrahive.update.plist").read_text() == "neu-update"   # nicht in der Sicherung
    calls = _calls(rb)
    starts = [c for c in calls if c.startswith("launchctl bootstrap system")]
    assert starts and starts[0].endswith("io.hydrahive.postgres.plist")              # Datenbank zuerst


def test_never_touches_update_service(rb):
    """Läuft aus dem Update-Dienst – den nicht anhalten (Befund #605)."""
    r = _run(rb)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not any("io.hydrahive.update" in c for c in _calls(rb))


def test_refuses_root_as_old_user(rb):
    r = _run(rb, HH_OLD_USER="root")
    assert r.returncode != 0
    assert _calls(rb) == []
