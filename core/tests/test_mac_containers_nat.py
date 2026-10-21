"""Container auf dem Mac (Plan docs/plans/mac-containers.md, Task f4a303a9): Netzmodi.

Unter Linux prüft nat.py /sys/class/net (br0 → bridged, hhnat0 → nat). Auf dem Mac gibt es /sys nicht; Incus läuft
in einer Linux-VM (Colima). Dort gilt: bridged nie (keine Brücke ins Heimnetz), nat, wenn das Incus-Netz hhnat0 in
der VM existiert. Der Linux-Weg muss unverändert bleiben.
"""
from __future__ import annotations

import pytest

from hydrahive.containers import _platform, nat


# --- Plattform ---------------------------------------------------------------------------------------

def test_is_mac_reads_sys_platform(monkeypatch):
    monkeypatch.setattr(_platform.sys, "platform", "darwin")
    assert _platform.is_mac() is True
    monkeypatch.setattr(_platform.sys, "platform", "linux")
    assert _platform.is_mac() is False


# --- Linux: /sys wie bisher -----------------------------------------------------------------------------

@pytest.fixture
def linux(monkeypatch, tmp_path):
    monkeypatch.setattr(_platform, "is_mac", lambda: False)
    monkeypatch.setattr(nat, "_sys_net", lambda: tmp_path)
    # Ein Aufruf von incus wäre unter Linux ein Fehler (dort entscheidet /sys).
    monkeypatch.setattr(nat, "_incus_network_exists", lambda name: pytest.fail("incus unter Linux gefragt"))
    return tmp_path


def test_linux_bridged_from_sys(linux):
    (linux / "br0").mkdir()
    assert nat.network_modes() == {"bridged": True, "nat": False, "isolated": True, "default": "bridged"}


def test_linux_nat_from_sys(linux):
    (linux / "hhnat0").mkdir()
    assert nat.network_modes() == {"bridged": False, "nat": True, "isolated": True, "default": "nat"}


def test_linux_nothing(linux):
    assert nat.network_modes() == {"bridged": False, "nat": False, "isolated": True, "default": "isolated"}


# --- Mac: Incus-Netz in der VM ----------------------------------------------------------------------------

@pytest.fixture
def mac(monkeypatch, tmp_path):
    monkeypatch.setattr(_platform, "is_mac", lambda: True)
    (tmp_path / "br0").mkdir()            # selbst wenn es so etwas gäbe: auf dem Mac nie bridged
    monkeypatch.setattr(nat, "_sys_net", lambda: tmp_path)
    return monkeypatch


def test_mac_nat_when_incus_network_exists(mac):
    mac.setattr(nat, "_incus_network_exists", lambda name: name == "hhnat0")
    assert nat.network_modes() == {"bridged": False, "nat": True, "isolated": True, "default": "nat"}


def test_mac_isolated_without_network(mac):
    mac.setattr(nat, "_incus_network_exists", lambda name: False)
    assert nat.network_modes() == {"bridged": False, "nat": False, "isolated": True, "default": "isolated"}


def test_incus_network_exists_uses_cli(monkeypatch):
    calls = []

    class R:
        def __init__(self, rc):
            self.returncode = rc

    def fake_run(args, **kw):
        calls.append(args)
        return R(0 if args[-1] == "hhnat0" else 1)

    monkeypatch.setattr(nat.subprocess, "run", fake_run)
    monkeypatch.setattr(nat.shutil, "which", lambda n: "/usr/local/lib/hydrahive2/containers/bin/incus")
    assert nat._incus_network_exists("hhnat0") is True
    assert nat._incus_network_exists("anders") is False
    assert calls[0] == ["/usr/local/lib/hydrahive2/containers/bin/incus", "network", "show", "hhnat0"]


def test_incus_network_exists_without_incus(monkeypatch):
    monkeypatch.setattr(nat.shutil, "which", lambda n: None)
    assert nat._incus_network_exists("hhnat0") is False


def test_wan_ipv4_on_mac_uses_route(monkeypatch):
    """`ip route` gibt es auf dem Mac nicht – WAN-Adresse über die Standardroute (route/ipconfig)."""
    monkeypatch.setattr(_platform, "is_mac", lambda: True)
    outputs = {
        # Volle Pfade: der Backend-Dienst hat /sbin und /usr/sbin nicht im PATH (Befund 21.10.2026, Test-Mac).
        ("/sbin/route", "-n", "get", "default"): "   route to: default\n  gateway: 192.168.178.1\n  interface: en1\n",
        ("/usr/sbin/ipconfig", "getifaddr", "en1"): "192.168.178.186\n",
    }

    class R:
        def __init__(self, out):
            self.stdout = out
            self.returncode = 0

    monkeypatch.setattr(nat.subprocess, "run", lambda args, **kw: R(outputs[tuple(args)]))
    assert nat.wan_interface() == "en1"
    assert nat.wan_ipv4() == "192.168.178.186"
