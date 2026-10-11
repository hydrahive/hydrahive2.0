"""hydrahive2-addon.service/.timer (Spec installer-core-first §3): frische Installation UND update.sh legen sie an.

Echtes Verhalten statt Textsuche, wo es ohne root geht: Der Unit-Block aus update.sh wird mit umgebogenen Pfaden
(SYSTEMD_DIR/LOG_DIR) und Ersatz-systemctl ausgeführt; geprüft werden die erzeugten Dateien.
"""
from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
FRESH = INSTALLER / "modules" / "50-systemd.sh"
UPDATE = INSTALLER / "update.sh"


def _unit_block(text: str, unit: str) -> str:
    m = re.search(rf"cat > [^\n]*{re.escape(unit)}[^\n]*<<EOF\n(.*?)\nEOF", text, re.S)
    assert m, f"{unit} wird nicht geschrieben"
    return m.group(1)


def test_fresh_install_writes_addon_units():
    text = FRESH.read_text()
    svc = text[text.index("ADDON_SERVICE=") - 1:]
    service = _unit_block(svc, "$ADDON_SERVICE")
    assert "ConditionPathExists=$HH_DATA_DIR/.addon_request" in service
    assert "ExecStart=$HH_REPO_DIR/installer/addon-ctl.sh" in service
    assert "StandardOutput=append:/var/log/hydrahive2-addon.log" in service
    assert "TimeoutStartSec=0" in service                       # Voice/VMs dauern lange
    assert "ExecStartPre" not in service                        # Anfrage bleibt bis zum Ende liegen (409-Schutz)
    timer = _unit_block(svc, "$ADDON_TIMER")
    assert "Unit=hydrahive2-addon.service" in timer
    assert "systemctl enable hydrahive2-addon.timer" in text
    assert "systemctl restart hydrahive2-addon.timer" in text
    assert "touch /var/log/hydrahive2-addon.log" in text


def _fake(bin_dir: Path, name: str, log: Path) -> None:
    p = bin_dir / name
    p.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n')
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


def test_update_sh_adds_addon_units_on_existing_servers(tmp_path):
    """Den update.sh-Abschnitt isoliert ausführen: legt Service+Timer an, startet den Timer – und lässt
    vorhandene Units in Ruhe (zweiter Lauf schreibt nichts neu)."""
    text = UPDATE.read_text()
    start = text.index("# --- Zusatz-Module-Runner (hydrahive2-addon)")
    end = text.index("# --- Ende Zusatz-Module-Runner", start)
    block = text[start:end]
    block = block.replace("/etc/systemd/system", "$UNIT_DIR").replace("/var/log", "$LOG_DIR")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    _fake(bin_dir, "systemctl", calls)
    units, logs = tmp_path / "units", tmp_path / "logs"
    units.mkdir()
    logs.mkdir()
    script = "set -euo pipefail\nlog() { :; }\n" + block
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "UNIT_DIR": str(units), "LOG_DIR": str(logs),
           "HH_DATA_DIR": "/var/lib/hydrahive2", "HH_CONFIG_DIR": "/etc/hydrahive2", "HH_REPO_DIR": "/opt/hydrahive2",
           "HH_USER": "hydrahive"}
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    service = (units / "hydrahive2-addon.service").read_text()
    assert "ExecStart=/opt/hydrahive2/installer/addon-ctl.sh" in service
    assert "ConditionPathExists=/var/lib/hydrahive2/.addon_request" in service
    assert "Unit=hydrahive2-addon.service" in (units / "hydrahive2-addon.timer").read_text()
    assert (logs / "hydrahive2-addon.log").exists()
    assert "systemctl enable hydrahive2-addon.timer" in calls.read_text()
    calls.unlink()
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert not calls.exists()                                   # schon da → nichts tun


def test_addon_ctl_is_executable_in_git():
    out = subprocess.run(["git", "ls-files", "-s", "installer/addon-ctl.sh"], cwd=INSTALLER.parent,
                         capture_output=True, text=True).stdout
    assert out.startswith("100755"), out
