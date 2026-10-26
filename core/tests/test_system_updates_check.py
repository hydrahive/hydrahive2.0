"""Admin-Konsole: offene Systemupdates und „Neustart nötig“ (docs/specs/system-updates.md, Task f24c39bf)."""
from __future__ import annotations

import subprocess

import pytest

from hydrahive.api.routes import _system_updates as su

SIM = (
    "Reading package lists...\n"
    "Inst libsystemd0 [259.5] (259.9 Ubuntu:26.04/resolute-updates [amd64])\n"
    "Inst gh [2.103.0] (2.103.2 gh:cli.github.com [amd64])\n"
    "Conf libsystemd0 (259.9 Ubuntu:26.04/resolute-updates [amd64])\n"
)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch, tmp_path):
    su._cache.clear()
    monkeypatch.setattr(su.settings, "reboot_required_file", tmp_path / "reboot-required", raising=False)
    monkeypatch.setattr(su.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    yield
    su._cache.clear()


def _fake_run(monkeypatch, out: str = SIM, rc: int = 0, counter: list | None = None):
    def run(cmd, **kw):
        if counter is not None:
            counter.append(cmd)
        assert cmd[0] == "apt-get" and "-s" in cmd and "upgrade" in cmd and "--with-new-pkgs" in cmd
        assert kw.get("timeout")
        return subprocess.CompletedProcess(cmd, rc, out, "")
    monkeypatch.setattr(su.subprocess, "run", run)


def test_zaehlt_inst_zeilen(monkeypatch) -> None:
    _fake_run(monkeypatch)
    c = su.check_system_updates()
    assert c == {"name_code": "system_updates", "ok": False, "detail_code": "sysupd_pending", "params": {"count": 2}}


def test_alles_aktuell(monkeypatch) -> None:
    _fake_run(monkeypatch, out="Reading package lists...\n")
    assert su.check_system_updates() == {"name_code": "system_updates", "ok": True, "detail_code": "sysupd_ok"}


def test_neustart_noetig(monkeypatch, tmp_path) -> None:
    _fake_run(monkeypatch, out="")
    (tmp_path / "reboot-required").touch()
    c = su.check_system_updates()
    assert c == {"name_code": "system_updates", "ok": False, "detail_code": "sysupd_reboot"}


def test_offen_und_neustart(monkeypatch, tmp_path) -> None:
    _fake_run(monkeypatch)
    (tmp_path / "reboot-required").touch()
    c = su.check_system_updates()
    assert c["detail_code"] == "sysupd_pending_reboot" and c["params"] == {"count": 2} and c["ok"] is False


def test_zwischenspeicher(monkeypatch) -> None:
    calls: list = []
    _fake_run(monkeypatch, counter=calls)
    su.check_system_updates()
    su.check_system_updates()
    assert len(calls) == 1


def test_zwischenspeicher_laeuft_ab(monkeypatch) -> None:
    calls: list = []
    _fake_run(monkeypatch, counter=calls)
    now = [1000.0]
    monkeypatch.setattr(su.time, "monotonic", lambda: now[0])
    su.check_system_updates()
    now[0] += su.CACHE_SECONDS - 1
    su.check_system_updates()
    assert len(calls) == 1
    now[0] += 2
    su.check_system_updates()
    assert len(calls) == 2


def test_neustart_marke_ohne_zwischenspeicher(monkeypatch, tmp_path) -> None:
    """Die Marke ist billig zu prüfen – nach einem Neustart soll der Hinweis sofort verschwinden."""
    _fake_run(monkeypatch, out="")
    (tmp_path / "reboot-required").touch()
    assert su.check_system_updates()["detail_code"] == "sysupd_reboot"
    (tmp_path / "reboot-required").unlink()
    assert su.check_system_updates()["detail_code"] == "sysupd_ok"


def test_ohne_apt_keine_pruefung(monkeypatch) -> None:
    monkeypatch.setattr(su.shutil, "which", lambda name: None)
    assert su.check_system_updates() is None


def test_apt_fehler_unbekannt(monkeypatch) -> None:
    _fake_run(monkeypatch, out="E: Could not open lock", rc=100)
    c = su.check_system_updates()
    assert c == {"name_code": "system_updates", "ok": False, "detail_code": "sysupd_unknown"}


def test_apt_timeout_unbekannt(monkeypatch) -> None:
    def run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 1))
    monkeypatch.setattr(su.subprocess, "run", run)
    assert su.check_system_updates()["detail_code"] == "sysupd_unknown"


def test_health_enthaelt_pruefung(monkeypatch) -> None:
    from hydrahive.api.routes import system
    monkeypatch.setattr(system, "check_system_updates", lambda: {"name_code": "system_updates", "ok": True,
                                                                 "detail_code": "sysupd_ok"})
    out = system.health(("admin", "admin"))
    assert [c["name_code"] for c in out["checks"]][-1] == "system_updates"


def test_health_ohne_apt_ohne_pruefung(monkeypatch) -> None:
    from hydrahive.api.routes import system
    monkeypatch.setattr(system, "check_system_updates", lambda: None)
    out = system.health(("admin", "admin"))
    assert all(c.get("name_code") != "system_updates" for c in out["checks"])


def test_setting_standardpfad(monkeypatch) -> None:
    from pathlib import Path
    from hydrahive.settings.settings import Settings
    monkeypatch.delenv("HH_REBOOT_REQUIRED_FILE", raising=False)
    assert Settings().reboot_required_file == Path("/run/reboot-required")
    monkeypatch.setenv("HH_REBOOT_REQUIRED_FILE", "/x/y")
    assert Settings().reboot_required_file == Path("/x/y")
