"""Update richtet incus nicht neu ein, wenn es schon läuft (docs/specs/incus-init-update.md, Task 004d8ee0).

Am 29.10. hat update.sh incus auf dem Hauptserver neu eingerichtet, weil der Speicher „ssd“ hieß und nicht „default“.
Ein nachgebautes `incus` im PATH schreibt jeden Aufruf mit; ausgeführt wird die echte installer/lib/incus-init.sh.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "installer" / "lib" / "incus-init.sh"
UPDATE = ROOT / "installer" / "update.sh"
CONTAINERS = ROOT / "installer" / "modules" / "70-containers.sh"

_FAKE = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
if [ "$1 $2" = "admin init" ]; then cat >> "$FAKE_LOG.preseed"; exit 0; fi
if [ "$1 $2" = "admin waitready" ]; then exit "${FAKE_RC:-0}"; fi
if [ "$1 $2" = "storage list" ]; then
  [ "${FAKE_RC:-0}" = 0 ] || { printf '%s' "${FAKE_ERR_OUT:-}"; echo "Error: daemon not reachable" >&2; exit 1; }
  printf '%s' "${FAKE_POOLS:-}"; exit 0
fi
exit 0
"""


def _run(tmp: Path, call: str, pools: str = "", rc: int = 0,
         err_out: str = "") -> tuple[subprocess.CompletedProcess, list[str], str]:
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    fake = bindir / "incus"
    fake.write_text(_FAKE)
    fake.chmod(0o755)
    log = tmp / "calls.log"
    log.write_text("")
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "FAKE_LOG": str(log),
           "FAKE_POOLS": pools, "FAKE_RC": str(rc), "FAKE_ERR_OUT": err_out}
    r = subprocess.run(["bash", "-c", f'set -euo pipefail; log() {{ echo "LOG: $*"; }}; source "$1"; {call}',
                        "t", str(LIB)], env=env, capture_output=True, text=True, timeout=30)
    pre = tmp / "calls.log.preseed"
    return r, log.read_text().splitlines(), pre.read_text() if pre.exists() else ""


def _inits(calls: list[str]) -> list[str]:
    return [c for c in calls if c.startswith("admin init")]


def test_nur_speicher_ssd_wird_nicht_neu_eingerichtet(tmp_path):
    r, calls, _ = _run(tmp_path, "ensure_incus_initialized", pools="ssd,btrfs,,12,CREATED\n")
    assert r.returncode == 0, r.stderr
    assert _inits(calls) == []
    assert not any(c.startswith(("profile", "storage create", "storage delete")) for c in calls)


def test_nur_speicher_ssd_gilt_als_eingerichtet(tmp_path):
    r, _, _ = _run(tmp_path, "incus_is_initialized", pools="ssd,btrfs,,12,CREATED\n")
    assert r.returncode == 0, r.stderr


def test_speicher_default_dir_bleibt_wie_er_ist(tmp_path):
    r, calls, _ = _run(tmp_path, "ensure_incus_initialized", pools="default,dir,,2,CREATED\n")
    assert r.returncode == 0 and _inits(calls) == []


def test_ohne_speicher_wird_einmal_eingerichtet(tmp_path):
    r, calls, preseed = _run(tmp_path, "ensure_incus_initialized", pools="")
    assert r.returncode == 0, r.stderr
    assert _inits(calls) == ["admin init --preseed"]
    assert "name: default" in preseed and "driver: dir" in preseed and "pool: default" in preseed


def test_ohne_speicher_gilt_als_nicht_eingerichtet(tmp_path):
    r, _, _ = _run(tmp_path, "incus_is_initialized", pools="")
    assert r.returncode != 0


def test_incus_antwortet_nicht_nichts_ueberschreiben(tmp_path):
    r, calls, _ = _run(tmp_path, "ensure_incus_initialized", rc=1)
    assert r.returncode == 0, r.stderr
    assert _inits(calls) == []
    assert "LOG: " in r.stdout and "antwortet nicht" in r.stdout


def test_incus_antwortet_nicht_gilt_nicht_als_eingerichtet(tmp_path):
    r, _, _ = _run(tmp_path, "incus_is_initialized", rc=1)
    assert r.returncode != 0


def test_update_fragt_nicht_mehr_nach_dem_namen_default():
    t = UPDATE.read_text()
    assert 'grep -q "default"' not in t
    assert "installer/lib/incus-init.sh" in t and "incus_is_initialized" in t


def test_containers_skript_nutzt_die_gemeinsame_funktion():
    t = CONTAINERS.read_text()
    assert "admin init" not in t
    assert "incus-init.sh" in t and "ensure_incus_initialized" in t


def test_fehler_zaehlt_auch_wenn_incus_dabei_etwas_ausgibt(tmp_path):
    """Nur der Rückgabewert entscheidet – nicht, ob zufällig Text auf stdout landet."""
    r, _, _ = _run(tmp_path, "incus_is_initialized", rc=1, err_out="ssd,btrfs,,12,CREATED\n")
    assert r.returncode != 0


def test_nur_leerzeilen_heisst_kein_speicher(tmp_path):
    r, calls, _ = _run(tmp_path, "ensure_incus_initialized", pools="  \n\n")
    assert r.returncode == 0, r.stderr
    assert _inits(calls) == ["admin init --preseed"]
