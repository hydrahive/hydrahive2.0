"""Gemeinsame Laufwerk-Attrappen für die Lösch-Tests (Fehler 1, Spec archiv-system.md)."""
from __future__ import annotations

import os

import pytest


def mount(project_id: str, name: str = "nas"):
    """Ein „eingehängtes“ NAS im Projekt: Datei liegt drin, Zuweisung in der DB."""
    from hydrahive.smbmounts import db as mounts_db
    from hydrahive.smbmounts.mounter import mountpoint_for
    m = mounts_db.create_mount(owner="testuser", name=name, host="nas.local", share="daten")
    mounts_db.set_project(m.mount_id, project_id)
    mounts_db.set_state(m.mount_id, "mounted")
    mp = mountpoint_for(project_id, name)
    os.makedirs(mp, exist_ok=True)
    with open(os.path.join(mp, "auf-dem-nas.txt"), "w") as fh:
        fh.write("darf nie weg")
    return m, mp


@pytest.fixture
def fake_mounts(monkeypatch):
    """os.path.ismount für die Test-Mountpunkte; umount kann scheitern oder klappen."""
    import hydrahive.smbmounts.mounter as mounter
    active: set[str] = set()
    real = os.path.ismount
    monkeypatch.setattr(os.path, "ismount", lambda p: str(p) in active or real(p))
    state = {"fail": False}

    def umount(m):
        if state["fail"]:
            return False, "umount_failed"
        active.discard(mounter.mountpoint_for(m.project_id, m.name))
        return True, "ok"

    monkeypatch.setattr(mounter, "umount", umount)
    return active, state
