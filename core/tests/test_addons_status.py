"""Zustand der Zusatz-Module für das Cockpit (Spec installer-core-first §3): installiert, gewünscht, Hinweise."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.system import addons_status as st

ALL = ["containers", "vms", "samba", "whatsapp", "voice", "tailscale"]


@pytest.fixture
def probes(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Alle Zustandsprüfungen durch einen Schalter je Modul ersetzen (Standard: nichts installiert)."""
    state = {a: False for a in ALL}
    monkeypatch.setattr(st, "PROBES", {a: (lambda a=a: state[a]) for a in ALL})
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    return state


def _by_id(items: list[dict]) -> dict[str, dict]:
    return {i["id"]: i for i in items}


def test_lists_exactly_the_six_addons_in_fixed_order(probes, tmp_path):
    items = st.list_addons(tmp_path / "install.conf")
    assert [i["id"] for i in items] == ALL


def test_installed_comes_from_probe(probes, tmp_path):
    probes["samba"] = True
    items = _by_id(st.list_addons(tmp_path / "install.conf"))
    assert items["samba"]["installed"] is True
    assert items["vms"]["installed"] is False


def test_enabled_comes_from_install_conf(probes, tmp_path):
    conf = tmp_path / "install.conf"
    conf.write_text("# Kopf\nHH_INSTALL_VMS='yes'\nHH_INSTALL_SAMBA=\"no\"\nHH_INSTALL_VOICE=yes\n")
    items = _by_id(st.list_addons(conf))
    assert items["vms"]["enabled"] is True
    assert items["voice"]["enabled"] is True
    assert items["samba"]["enabled"] is False
    assert items["whatsapp"]["enabled"] is False                # fehlt → nicht gewünscht


def test_unreadable_or_missing_install_conf_means_not_enabled(probes, tmp_path):
    items = st.list_addons(tmp_path / "gibt-es-nicht.conf")
    assert all(i["enabled"] is False for i in items)


def test_restart_flag_only_for_vms_and_containers(probes, tmp_path):
    items = _by_id(st.list_addons(tmp_path / "install.conf"))
    assert {a for a, i in items.items() if i["restarts_service"]} == {"vms", "containers"}


def test_voice_needs_containers(probes, tmp_path):
    items = _by_id(st.list_addons(tmp_path / "install.conf"))
    assert items["voice"]["requires"] == ["containers"]
    assert items["samba"]["requires"] == []


def test_wsl_hint_for_vms_containers_voice(probes, monkeypatch, tmp_path):
    monkeypatch.setattr(st, "is_wsl", lambda: True)
    items = _by_id(st.list_addons(tmp_path / "install.conf"))
    assert {a for a, i in items.items() if i["hint"] == "wsl"} == {"vms", "containers", "voice"}
    monkeypatch.setattr(st, "is_wsl", lambda: False)
    assert all(i["hint"] is None for i in st.list_addons(tmp_path / "install.conf"))


def test_probe_error_counts_as_not_installed(probes, monkeypatch, tmp_path):
    def boom() -> bool:
        raise OSError("kaputt")
    monkeypatch.setattr(st, "PROBES", {**st.PROBES, "samba": boom})
    assert _by_id(st.list_addons(tmp_path / "install.conf"))["samba"]["installed"] is False


def test_is_wsl_reads_proc(tmp_path, monkeypatch):
    version = tmp_path / "version"
    version.write_text("Linux version 6.6.87.2-microsoft-standard-WSL2 (gcc)\n")
    monkeypatch.setattr(st, "_PROC_VERSION", version)
    monkeypatch.setattr(st, "_WSL_INTEROP", tmp_path / "nicht-da")
    assert st.is_wsl() is True
    version.write_text("Linux version 6.8.0-45-generic (buildd@lcy02)\n")
    assert st.is_wsl() is False
    interop = tmp_path / "WSLInterop"
    interop.write_text("")
    monkeypatch.setattr(st, "_WSL_INTEROP", interop)
    assert st.is_wsl() is True


def test_vms_probe_needs_vm_manager_unit_and_qemu(monkeypatch, tmp_path):
    """qemu allein reicht nicht – incus bringt es als Abhängigkeit mit (Fund hh-instcore 11.10.2026). Installiert ist der
    VM-Manager, wenn seine Unit (nur von 65-vms.sh angelegt) da ist und qemu vorhanden ist."""
    unit = tmp_path / "hydrahive2-websockify.service"
    monkeypatch.setattr(st, "_VM_UNIT", unit)
    monkeypatch.setattr(st.shutil, "which", lambda name: "/usr/bin/qemu-system-x86_64")
    assert st._vms_installed() is False                         # nur qemu (z. B. über incus) → nicht installiert
    unit.write_text("[Unit]\n")
    assert st._vms_installed() is True
    monkeypatch.setattr(st.shutil, "which", lambda name: None)
    assert st._vms_installed() is False


def test_whatsapp_probe_checks_node_modules(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(st, "_WA_BRIDGE", tmp_path)
    assert st._whatsapp_installed() is False
    (tmp_path / "node_modules").mkdir()
    assert st._whatsapp_installed() is True
