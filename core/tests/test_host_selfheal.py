"""Host-Self-Heal nach Ubuntu-26.04-Upgrade.

Siehe docs/specs/host-selfheal-ubuntu-2604.md.

Die Funktionen aus installer/lib/host-selfheal.sh greifen tief ins System ein
(systemctl, incus, resolved). Getestet wird deshalb gegen PATH-Stubs: jedes
Systemkommando ist ein Shell-Skript im tmp_path, das seine Aufrufe protokolliert
und ein vorgegebenes Verhalten simuliert. So laufen die Tests ohne root und
ohne echte Systemänderung.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "installer" / "lib" / "host-selfheal.sh"
UPDATE_SCRIPT = REPO_ROOT / "installer" / "update.sh"
VOICE_SCRIPT = REPO_ROOT / "installer" / "modules" / "55-voice.sh"


def _calls(path: Path) -> str:
    """Protokollierte Aufrufe. Fehlt die Datei, wurde nichts aufgerufen."""
    return path.read_text() if path.exists() else ""


def _write_stub(bin_dir: Path, name: str, body: str) -> None:
    stub = bin_dir / name
    stub.write_text(f"#!/usr/bin/env bash\n{body}\n")
    stub.chmod(0o755)


def _run(
    command: str,
    bin_dir: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Sourced den Helper und führt `command` mit gestubbtem PATH aus."""
    return subprocess.run(
        [
            "bash",
            "-c",
            f'set -uo pipefail; source "$1"; {command}',
            "test-host-selfheal",
            str(HELPER),
        ],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(bin_dir),
            "LANG": "C.UTF-8",
            **(env or {}),
        },
    )


def _systemctl_stub(bin_dir: Path, *, masked: str = "", active: str = "") -> Path:
    """systemctl-Stub. `masked`/`active` sind Leerzeichen-Listen von Units."""
    calls = bin_dir / "systemctl.calls"
    _write_stub(
        bin_dir,
        "systemctl",
        f"""
echo "$*" >> {calls}
case "$1" in
  is-enabled)
    for u in {masked or "''"}; do [ "$u" = "$2" ] && {{ echo masked; exit 0; }}; done
    echo enabled; exit 0 ;;
  is-active)
    for u in {active or "''"}; do [ "$u" = "$2" ] && {{ echo active; exit 0; }}; done
    echo inactive; exit 3 ;;
  cat)
    for u in {active or "''"}; do [ "$u" = "$2" ] && exit 0; done
    exit 1 ;;
esac
exit 0
""",
    )
    return calls


# ── tmp.mount ────────────────────────────────────────────────────────────────


def test_tmp_on_tmpfs_gets_masked(tmp_path: Path) -> None:
    """Ist /tmp eine RAM-Disk, muss tmp.mount maskiert werden."""
    calls = _systemctl_stub(tmp_path)
    _write_stub(tmp_path, "findmnt", 'echo tmpfs')

    result = _run("hh_fix_tmp_on_tmpfs", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "mask tmp.mount" in _calls(calls)


def test_tmp_on_disk_is_left_alone(tmp_path: Path) -> None:
    """Liegt /tmp auf Platte, darf nichts angefasst werden."""
    calls = _systemctl_stub(tmp_path)
    _write_stub(tmp_path, "findmnt", 'echo ext4')

    result = _run("hh_fix_tmp_on_tmpfs", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "mask" not in _calls(calls)


def test_tmp_mask_is_idempotent(tmp_path: Path) -> None:
    """Bereits maskiert: kein zweiter mask-Aufruf."""
    calls = _systemctl_stub(tmp_path, masked="tmp.mount")
    _write_stub(tmp_path, "findmnt", 'echo tmpfs')

    result = _run("hh_fix_tmp_on_tmpfs", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "mask" not in _calls(calls)


# ── systemd-resolved-Stub ────────────────────────────────────────────────────


def test_resolved_stub_disabled_when_pihole_present(tmp_path: Path) -> None:
    """Mit Pi-hole auf :53 muss der Stub-Listener per Drop-in weichen."""
    conf_dir = tmp_path / "resolved.conf.d"
    resolv = tmp_path / "resolv.conf"
    resolv.symlink_to("/run/systemd/resolve/stub-resolv.conf")
    _systemctl_stub(tmp_path, active="pihole-FTL")
    _write_stub(tmp_path, "ss", 'echo "UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:* users:((\\"systemd-resolve\\",pid=1,fd=1))"')

    result = _run(
        "hh_fix_resolved_stub",
        tmp_path,
        env={"HH_RESOLVED_CONF_DIR": str(conf_dir), "HH_RESOLV_CONF": str(resolv)},
    )

    assert result.returncode == 0, result.stderr
    dropin = conf_dir / "10-hydrahive-no-stub.conf"
    assert dropin.exists()
    assert "DNSStubListener=no" in dropin.read_text()
    assert os.readlink(resolv).endswith("/run/systemd/resolve/resolv.conf")


def test_resolved_stub_kept_without_host_dns_server(tmp_path: Path) -> None:
    """Ohne eigenen DNS-Server ist der Stub korrekt und bleibt unangetastet."""
    conf_dir = tmp_path / "resolved.conf.d"
    resolv = tmp_path / "resolv.conf"
    resolv.symlink_to("/run/systemd/resolve/stub-resolv.conf")
    _systemctl_stub(tmp_path)
    _write_stub(tmp_path, "ss", "echo ''")

    result = _run(
        "hh_fix_resolved_stub",
        tmp_path,
        env={"HH_RESOLVED_CONF_DIR": str(conf_dir), "HH_RESOLV_CONF": str(resolv)},
    )

    assert result.returncode == 0, result.stderr
    assert not (conf_dir / "10-hydrahive-no-stub.conf").exists()
    assert os.readlink(resolv).endswith("stub-resolv.conf")


def test_resolved_dropin_is_idempotent(tmp_path: Path) -> None:
    """Zweiter Lauf startet resolved nicht erneut neu."""
    conf_dir = tmp_path / "resolved.conf.d"
    conf_dir.mkdir()
    (conf_dir / "10-hydrahive-no-stub.conf").write_text(
        "[Resolve]\nDNSStubListener=no\n"
    )
    resolv = tmp_path / "resolv.conf"
    resolv.symlink_to("/run/systemd/resolve/resolv.conf")
    calls = _systemctl_stub(tmp_path, active="pihole-FTL")
    _write_stub(tmp_path, "ss", "echo ''")

    result = _run(
        "hh_fix_resolved_stub",
        tmp_path,
        env={"HH_RESOLVED_CONF_DIR": str(conf_dir), "HH_RESOLV_CONF": str(resolv)},
    )

    assert result.returncode == 0, result.stderr
    assert "restart systemd-resolved" not in _calls(calls)


# ── Incus-Bridge-DNS ─────────────────────────────────────────────────────────


def _incus_stub(bin_dir: Path, *, networks: str = "hh-voice", raw: str = "") -> Path:
    calls = bin_dir / "incus.calls"
    _write_stub(
        bin_dir,
        "incus",
        f"""
echo "$*" >> {calls}
if [ "$1" = network ] && [ "$2" = list ]; then
  for n in {networks or "''"}; do echo "$n,bridge,YES"; done
  exit 0
fi
if [ "$1" = network ] && [ "$2" = get ]; then echo '{raw}'; exit 0; fi
exit 0
""",
    )
    return calls


def test_bridge_dns_disabled_when_host_dns_present(tmp_path: Path) -> None:
    """Bridge-dnsmasq darf Port 53 nicht belegen, wenn Pi-hole ihn braucht."""
    calls = _incus_stub(tmp_path)
    _systemctl_stub(tmp_path, active="pihole-FTL")

    result = _run("hh_fix_incus_bridge_dns", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "network set hh-voice raw.dnsmasq port=0" in _calls(calls)


def test_bridge_dns_untouched_without_host_dns(tmp_path: Path) -> None:
    """Ohne Host-DNS-Server gibt es keinen Konflikt — nicht eingreifen."""
    calls = _incus_stub(tmp_path)
    _systemctl_stub(tmp_path)

    result = _run("hh_fix_incus_bridge_dns", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "raw.dnsmasq" not in _calls(calls)


def test_bridge_dns_fix_is_idempotent(tmp_path: Path) -> None:
    """port=0 bereits gesetzt: kein erneutes Schreiben."""
    calls = _incus_stub(tmp_path, raw="port=0")
    _systemctl_stub(tmp_path, active="pihole-FTL")

    result = _run("hh_fix_incus_bridge_dns", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "network set" not in _calls(calls)


def test_bridge_fix_skipped_without_incus(tmp_path: Path) -> None:
    """Ohne incus-Binary darf die Funktion nicht scheitern."""
    _systemctl_stub(tmp_path, active="pihole-FTL")

    result = _run("hh_fix_incus_bridge_dns", tmp_path)

    assert result.returncode == 0, result.stderr


# ── Pi-hole-Startreihenfolge ─────────────────────────────────────────────────


def test_pihole_ordered_after_incus(tmp_path: Path) -> None:
    """Boot-Race absichern: pihole-FTL erst nach incus starten."""
    dropin_root = tmp_path / "system"
    _systemctl_stub(tmp_path, active="pihole-FTL")
    _incus_stub(tmp_path)

    result = _run(
        "hh_fix_pihole_ordering",
        tmp_path,
        env={"HH_SYSTEMD_SYSTEM_DIR": str(dropin_root)},
    )

    assert result.returncode == 0, result.stderr
    dropin = dropin_root / "pihole-FTL.service.d" / "10-after-incus.conf"
    assert dropin.exists()
    assert "After=incus.service" in dropin.read_text()


def test_pihole_ordering_skipped_when_absent(tmp_path: Path) -> None:
    """Ohne Pi-hole entsteht kein Drop-in."""
    dropin_root = tmp_path / "system"
    _systemctl_stub(tmp_path)
    _incus_stub(tmp_path)

    result = _run(
        "hh_fix_pihole_ordering",
        tmp_path,
        env={"HH_SYSTEMD_SYSTEM_DIR": str(dropin_root)},
    )

    assert result.returncode == 0, result.stderr
    assert not (dropin_root / "pihole-FTL.service.d").exists()


# ── Wirkprüfung ──────────────────────────────────────────────────────────────


def test_broken_dns_triggers_restart(tmp_path: Path) -> None:
    """Antwortet der DNS-Server nicht, wird er genau einmal neu gestartet."""
    calls = _systemctl_stub(tmp_path, active="pihole-FTL")
    _write_stub(tmp_path, "dig", "exit 9")

    result = _run("hh_verify_dns", tmp_path)

    assert "restart pihole-FTL" in _calls(calls)
    assert "DNS" in (result.stdout + result.stderr)


def test_working_dns_is_not_restarted(tmp_path: Path) -> None:
    """Funktioniert DNS, darf der Dienst nicht angefasst werden."""
    calls = _systemctl_stub(tmp_path, active="pihole-FTL")
    _write_stub(tmp_path, "dig", "echo 140.82.121.3")

    result = _run("hh_verify_dns", tmp_path)

    assert result.returncode == 0, result.stderr
    assert "restart" not in _calls(calls)


# ── Verdrahtung ──────────────────────────────────────────────────────────────


def test_update_sources_and_runs_host_selfheal() -> None:
    """update.sh muss die Reparaturen tatsächlich aufrufen."""
    text = UPDATE_SCRIPT.read_text()

    assert "installer/lib/host-selfheal.sh" in text
    for fn in (
        "hh_fix_tmp_on_tmpfs",
        "hh_fix_resolved_stub",
        "hh_fix_incus_bridge_dns",
        "hh_fix_pihole_ordering",
        "hh_verify_dns",
    ):
        assert fn in text, f"{fn} fehlt in update.sh"


def test_voice_bridge_created_without_dns() -> None:
    """Neue Voice-Bridges dürfen gar nicht erst Port 53 belegen."""
    text = VOICE_SCRIPT.read_text()

    assert "raw.dnsmasq=port=0" in text


def test_selfheal_helper_is_syntactically_valid() -> None:
    result = subprocess.run(
        ["bash", "-n", str(HELPER)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
