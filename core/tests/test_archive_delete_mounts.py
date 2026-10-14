"""Projekt löschen mit eingehängten Laufwerken: nie ins NAS löschen (Fehler 1, Spec archiv-system.md)."""
from __future__ import annotations

import os

import pytest

from hydrahive.archive import deletion
from tests._delete_fixtures import make_project
from tests._delete_mounts import mount as _mount

pytest_plugins = ["tests._delete_env", "tests._delete_mounts"]  # Fixtures `archive_root`, `fake_mounts`


@pytest.mark.parametrize("mode", ["archive", "permanent"])
def test_failed_umount_deletes_nothing(archive_root, fake_mounts, mode) -> None:
    """Fehler 1: Scheitert das Aushängen, darf nichts gelöscht werden – schon gar nicht auf dem NAS."""
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    from hydrahive.projects._paths import workspace_path
    active, state = fake_mounts
    p = make_project(f"Haengt D {mode}")
    _m, mp = _mount(p["id"])
    active.add(mp)
    state["fail"] = True

    result = deletion.run("project", p["id"], mode, actor="admin")

    assert result["state"] == "failed" and result["error"] == "umount_failed"
    assert os.path.exists(os.path.join(mp, "auf-dem-nas.txt"))
    assert project_config.get(p["id"]) is not None and (workspace_path(p["id"]) / "code.py").exists()
    assert agent_config.get(p["agent_id"])["status"] == "active"


def test_project_config_delete_never_deletes_into_mount(fake_mounts) -> None:
    """Fehler 1 auch im internen Löschen (projects/config.delete)."""
    from hydrahive.agents import config as agent_config
    from hydrahive.projects import config as project_config
    active, state = fake_mounts
    p = make_project("Intern E")
    _m, mp = _mount(p["id"])
    active.add(mp)
    state["fail"] = True

    with pytest.raises(project_config.ProjectDeleteBlocked):
        project_config.delete(p["id"])

    assert os.path.exists(os.path.join(mp, "auf-dem-nas.txt"))
    assert project_config.get(p["id"]) is not None and agent_config.get(p["agent_id"]) is not None


def test_umount_says_ok_but_still_mounted_deletes_nothing(archive_root, fake_mounts, monkeypatch) -> None:
    """Meldet umount „ok“, hängt das Laufwerk aber noch: wie gescheitert behandeln."""
    import hydrahive.smbmounts.mounter as mounter
    from hydrahive.projects import config as project_config
    active, _ = fake_mounts
    p = make_project("Luegt F")
    _m, mp = _mount(p["id"])
    active.add(mp)
    monkeypatch.setattr(mounter, "umount", lambda m: (True, "ok"))

    result = deletion.run("project", p["id"], "permanent", actor="admin")

    assert result["state"] == "failed" and result["error"] == "umount_failed"
    assert os.path.exists(os.path.join(mp, "auf-dem-nas.txt")) and project_config.get(p["id"]) is not None


def test_unregistered_mount_is_never_entered(archive_root, fake_mounts) -> None:
    """Ein Laufwerk, das HydraHive nicht kennt (von Hand eingehängt): stehen lassen und melden."""
    from hydrahive.projects import config as project_config
    from hydrahive.projects._paths import workspace_path
    active, _ = fake_mounts
    p = make_project("Fremd G")
    mp = workspace_path(p["id"]) / "daten" / "usb"
    mp.mkdir(parents=True)
    (mp / "foto.jpg").write_text("bild")
    active.add(str(mp))

    result = deletion.run("project", p["id"], "permanent", actor="admin")

    assert result["state"] == "done" and result["leftovers"] == [str(mp)]
    assert (mp / "foto.jpg").exists() and not (workspace_path(p["id"]) / "code.py").exists()
    assert project_config.get(p["id"]) is None
