"""Zusatz-Module auf dem Mac (Pläne docs/plans/mac-containers.md §3, mac-tailscale.md): nur „Container“ und
„Tailscale“ lassen sich dort nachinstallieren.

Die übrigen Module (VMs, Samba, WhatsApp, Voice) bauen auf apt/systemd bzw. Linux-Diensten auf. Auf dem Mac zeigt das
Cockpit sie mit Hinweis „mac“ und ohne Installieren; die API lehnt sie ab. Linux unverändert.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.system import addons_status as st

ALL = ["containers", "vms", "samba", "whatsapp", "voice", "tailscale"]


@pytest.fixture
def probes(monkeypatch):
    state = {a: False for a in ALL}
    monkeypatch.setattr(st, "PROBES", {a: (lambda a=a: state[a]) for a in ALL})
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    return state


def test_mac_only_containers_voice_and_tailscale_installable(probes, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "is_mac", lambda: True)
    items = {i["id"]: i for i in st.list_addons(tmp_path / "install.conf")}
    assert items["containers"]["hint"] is None
    assert items["tailscale"]["hint"] is None
    assert items["voice"]["hint"] is None                       # docs/plans/mac-voice.md
    for other in ("vms", "samba", "whatsapp"):
        assert items[other]["hint"] == "mac", other


def test_mac_containers_needs_no_service_restart(probes, tmp_path, monkeypatch):
    """Linux: 70-containers.sh patcht hydrahive2.service. Mac: der Backend-PATH kommt aus der plist; der Runner startet
    das Backend selbst neu – der Hinweis „startet neu“ bleibt also richtig."""
    monkeypatch.setattr(st, "is_mac", lambda: True)
    items = {i["id"]: i for i in st.list_addons(tmp_path / "install.conf")}
    assert items["containers"]["restarts_service"] is True


def test_linux_unchanged(probes, tmp_path, monkeypatch):
    monkeypatch.setattr(st, "is_mac", lambda: False)
    items = st.list_addons(tmp_path / "install.conf")
    assert [i["hint"] for i in items] == [None] * 6


def test_api_refuses_mac_limited_addon(client, admin_headers, tmp_path, monkeypatch):
    from hydrahive.api.routes import system_addons

    monkeypatch.setattr(st, "is_mac", lambda: True)
    monkeypatch.setattr(st, "PROBES", {a: (lambda: False) for a in ALL})
    trigger = tmp_path / ".addon_request"
    monkeypatch.setattr(system_addons, "_trigger", lambda: trigger)
    monkeypatch.setattr(system_addons, "_install_conf", lambda: tmp_path / "install.conf")
    r = client.post("/api/system/addons/samba/install", headers=admin_headers)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "addon_unavailable_mac"
    assert not trigger.exists()
    r = client.post("/api/system/addons/containers/install", headers=admin_headers)
    assert r.status_code == 202
    assert trigger.read_text() == "install containers\n"


def test_is_mac_shared_with_containers():
    from hydrahive.containers import _platform

    assert st.is_mac is _platform.is_mac or st.is_mac.__module__ == "hydrahive.containers._platform"
