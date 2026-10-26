"""Systemupdates bei jedem HydraHive-Update (docs/specs/system-updates.md, Task f24c39bf).

Befund 26.10.2026: update.sh hob nie Systempakete an; hydratest hatte 225 offene Pakete und keine
automatischen Sicherheitsupdates. Getestet mit PATH-Attrappen für apt-get, dpkg und needrestart –
jede protokolliert ihre Aufrufe. Kein Netz, kein root; alle Zielpfade liegen in tmp_path.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "installer" / "lib" / "system-upgrade.sh"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    p = bin_dir / name
    p.write_text(f'#!/bin/bash\necho "{name} $*" >> "$CALLS"\n{body}\n')
    p.chmod(0o755)


@pytest.fixture
def env(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sysbin = tmp_path / "sysbin"
    sysbin.mkdir()
    for tool in ("bash", "cat", "grep", "mkdir", "chmod", "printf", "rm", "tail", "sed", "wc", "tr", "touch",
                 "head", "mktemp", "env", "tee", "dirname"):
        found = shutil.which(tool, path="/usr/bin:/bin")
        if found:
            (sysbin / tool).symlink_to(found)
    calls = tmp_path / "calls.log"
    installed = tmp_path / "installed"
    installed.mkdir()
    # dpkg -s PAKET: installiert, wenn installed/PAKET existiert (Attrappe für den Paketstand).
    _stub(bin_dir, "dpkg", f"""
if [ "$1" = -s ]; then [ -e "{installed}/$2" ]; exit $?; fi
[ -n "${{DPKG_FAIL:-}}" ] && exit 1
exit 0
""")
    # apt-get: install legt die Marke an; upgrade gibt die Paketzeilen aus UPGRADE_OUT aus.
    _stub(bin_dir, "apt-get", f"""
for a in "$@"; do
  case "$a" in
    update) [ -n "${{APT_UPDATE_FAIL:-}}" ] && exit 100 ;;
    upgrade) [ -n "${{APT_UPGRADE_FAIL:-}}" ] && {{ echo "E: dpkg was interrupted" >&2; exit 100; }}
             printf '%b' "${{UPGRADE_OUT:-}}"; exit 0 ;;
    install) seen=1 ;;
    -*) ;;
    *) [ -n "${{seen:-}}" ] && touch "{installed}/$a" ;;
  esac
done
exit 0
""")
    return {
        "bin": bin_dir, "sysbin": sysbin, "calls": calls, "installed": installed, "tmp": tmp_path,
        "apt_conf": tmp_path / "apt.conf.d" / "21hydrahive-auto-upgrades",
        "nr_conf": tmp_path / "needrestart" / "conf.d" / "50-hydrahive.conf",
        "reboot": tmp_path / "run" / "reboot-required",
    }


def run(env, func: str, **extra) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail; log(){{ echo "LOG $*"; }}; source "{LIB}"; {func}; echo "RC=$?"'
    e = {
        "PATH": f"{env['bin']}:{env['sysbin']}", "CALLS": str(env["calls"]),
        "HH_AUTO_UPGRADES_CONF": str(env["apt_conf"]), "HH_NEEDRESTART_CONF": str(env["nr_conf"]),
        "HH_REBOOT_REQUIRED_FILE": str(env["reboot"]), "TMPDIR": str(env["tmp"]),
    }
    e.update(extra)
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=e)


def calls(env) -> list[str]:
    return env["calls"].read_text().splitlines() if env["calls"].exists() else []


# --- hh_system_upgrade -------------------------------------------------------------------------------------------

def test_upgrade_reihenfolge_und_ohne_rueckfragen(env) -> None:
    r = run(env, "hh_system_upgrade", UPGRADE_OUT="Setting up a (1)\\nSetting up b (2)\\n")
    assert r.returncode == 0, r.stderr
    assert "RC=0" in r.stdout
    c = calls(env)
    i_cfg = next(i for i, x in enumerate(c) if x == "dpkg --configure -a")
    i_upd = next(i for i, x in enumerate(c) if x.startswith("apt-get") and x.endswith(" update"))
    i_upg = next(i for i, x in enumerate(c) if x.startswith("apt-get") and " upgrade" in x)
    assert i_cfg < i_upd < i_upg
    upg = c[i_upg]
    for flag in ("-y", "--with-new-pkgs", "Dpkg::Options::=--force-confdef", "Dpkg::Options::=--force-confold",
                 "DPkg::Lock::Timeout=600"):
        assert flag in upg.split(), (flag, upg)
    assert "Systempakete aktualisiert: 2" in r.stdout


def test_upgrade_ohne_rueckfrage_auch_fuer_debconf(env) -> None:
    """DEBIAN_FRONTEND=noninteractive muss beim apt-get-Aufruf gesetzt sein, sonst hängt ein Paket mit Dialog."""
    _stub(env["bin"], "apt-get", 'echo "FRONTEND=${DEBIAN_FRONTEND:-} NR=${NEEDRESTART_MODE:-}" >> "$CALLS"; exit 0')
    run(env, "hh_system_upgrade")
    lines = [x for x in calls(env) if x.startswith("FRONTEND=")]
    assert lines and all(x == "FRONTEND=noninteractive NR=a" for x in lines), lines


def test_upgrade_entfernt_nie_etwas(env) -> None:
    run(env, "hh_system_upgrade")
    joined = "\n".join(calls(env))
    for bad in ("full-upgrade", "dist-upgrade", "autoremove", " remove", " purge"):
        assert bad not in joined, bad


def test_upgrade_fehler_ist_nur_warnung(env) -> None:
    r = run(env, "hh_system_upgrade", APT_UPGRADE_FAIL="1")
    assert r.returncode == 0
    assert "RC=0" in r.stdout
    assert "WARNUNG: Systemupdate fehlgeschlagen" in r.stdout


def test_update_fehler_ist_nur_warnung_und_upgrade_laeuft_trotzdem(env) -> None:
    """Eine kaputte Fremdquelle darf die Ubuntu-Updates nicht verhindern."""
    r = run(env, "hh_system_upgrade", APT_UPDATE_FAIL="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG: Paketlisten nicht vollständig abrufbar" in r.stdout
    assert any(" upgrade" in x for x in calls(env))


def test_abgebrochenes_dpkg_wird_nur_gemeldet(env) -> None:
    r = run(env, "hh_system_upgrade", DPKG_FAIL="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG: dpkg --configure -a fehlgeschlagen" in r.stdout


def test_abschaltbar(env) -> None:
    r = run(env, "hh_system_upgrade", HH_SYSTEM_UPGRADE="no")
    assert "RC=0" in r.stdout
    assert not any(x.startswith(("apt-get", "dpkg")) for x in calls(env))
    assert "Systemupdate abgeschaltet (HH_SYSTEM_UPGRADE=no)" in r.stdout


def test_ohne_apt_nichts(env) -> None:
    (env["bin"] / "apt-get").unlink()
    r = run(env, "hh_system_upgrade")
    assert "RC=0" in r.stdout
    assert calls(env) == []


def test_neustart_noetig_wird_gemeldet(env) -> None:
    env["reboot"].parent.mkdir(parents=True)
    env["reboot"].touch()
    r = run(env, "hh_system_upgrade")
    assert "Neustart des Rechners nötig" in r.stdout


def test_kein_neustart_kein_hinweis(env) -> None:
    r = run(env, "hh_system_upgrade", UPGRADE_OUT="Setting up a (1)\\n")
    assert "Neustart" not in r.stdout
    assert not env["reboot"].exists()


def test_nvidia_angehoben_setzt_neustart_marke(env) -> None:
    r = run(env, "hh_system_upgrade", UPGRADE_OUT="Setting up libnvidia-gl-595:amd64 (595.1) ...\\n")
    assert env["reboot"].exists()
    assert "Neustart des Rechners nötig" in r.stdout


def test_andere_pakete_setzen_keine_neustart_marke(env) -> None:
    run(env, "hh_system_upgrade", UPGRADE_OUT="Setting up nvidia-ish-tool-doc-not (1)\\nSetting up curl (8)\\n")
    # „nvidia-ish…“ ist kein Treiberpaket – nur nvidia-<treiber>/libnvidia-* zählen.
    assert not env["reboot"].exists()


# --- hh_ensure_auto_updates --------------------------------------------------------------------------------------

def test_auto_updates_installiert_fehlende_pakete(env) -> None:
    r = run(env, "hh_ensure_auto_updates")
    assert "RC=0" in r.stdout
    inst = [x for x in calls(env) if x.startswith("apt-get") and " install" in x]
    assert inst and "unattended-upgrades" in inst[0].split() and "needrestart" in inst[0].split()


def test_auto_updates_vorhandene_pakete_nicht_neu(env) -> None:
    (env["installed"] / "unattended-upgrades").touch()
    (env["installed"] / "needrestart").touch()
    run(env, "hh_ensure_auto_updates")
    assert not any(x.startswith("apt-get") for x in calls(env))


def test_auto_updates_schreibt_apt_konfiguration(env) -> None:
    run(env, "hh_ensure_auto_updates")
    text = env["apt_conf"].read_text()
    assert 'APT::Periodic::Update-Package-Lists "1";' in text
    assert 'APT::Periodic::Unattended-Upgrade "1";' in text
    assert oct(env["apt_conf"].stat().st_mode & 0o777) == "0o644"


def test_needrestart_automatisch_ohne_hydrahive_und_container(env) -> None:
    run(env, "hh_ensure_auto_updates")
    text = env["nr_conf"].read_text()
    assert "$nrconf{restart} = 'a';" in text
    assert "$nrconf{kernelhints} = 0;" in text
    assert "$nrconf{ucodehints} = 0;" in text
    for unit in (r"qr(^hydrahive2) => 0", r"qr(^hydra-voice-bridge) => 0", r"qr(^incus) => 0",
                 r"qr(^containerd) => 0"):
        assert unit in text, unit


def test_auto_updates_idempotent(env) -> None:
    run(env, "hh_ensure_auto_updates")
    first = (env["apt_conf"].read_text(), env["nr_conf"].read_text())
    env["calls"].unlink(missing_ok=True)
    r = run(env, "hh_ensure_auto_updates")
    assert (env["apt_conf"].read_text(), env["nr_conf"].read_text()) == first
    assert "schreiben" not in r.stdout


def test_auto_updates_ohne_apt_nichts(env) -> None:
    (env["bin"] / "apt-get").unlink()
    r = run(env, "hh_ensure_auto_updates")
    assert "RC=0" in r.stdout
    assert not env["apt_conf"].exists() and not env["nr_conf"].exists()


def test_auto_updates_install_fehler_nur_warnung(env) -> None:
    _stub(env["bin"], "apt-get", "exit 100")
    r = run(env, "hh_ensure_auto_updates")
    assert "RC=0" in r.stdout
    assert "WARNUNG" in r.stdout
    # Konfiguration wird trotzdem geschrieben (greift, sobald die Pakete da sind).
    assert env["apt_conf"].exists()
