"""Projekt löschen: ein Paket mit allem, ohne Laufwerke; Fehler 1 (Spec archiv-system.md, Etappe 2)."""
from __future__ import annotations

import json
import os

import pytest

from hydrahive.archive import deletion
from tests._delete_fixtures import (
    make_agent, make_chat, make_project, meta, names, only_package, packages, read_member, session_exists,
)

pytest_plugins = ["tests._delete_fixtures"]  # Fixture `archive_root`


def _mount(project_id: str, name: str = "nas"):
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


def test_project_package_has_everything_but_mounts(archive_root, fake_mounts) -> None:
    from hydrahive.projects import config as project_config
    from hydrahive.projects._paths import workspace_path
    active, _ = fake_mounts
    p = make_project("Paket-Projekt A", members=["testuser", {"username": "admin", "role": "read"}])
    helper = make_agent("Helfer A", project_id=p["id"])
    chat_p, chat_h = make_chat(p["agent_id"], project_id=p["id"]), make_chat(helper["id"], project_id=p["id"])
    _m, mp = _mount(p["id"])
    active.add(mp)

    result = deletion.run("project", p["id"], "archive", actor="admin")

    assert result["state"] == "done", result
    tgz = only_package(archive_root, "projects")
    content = names(tgz)
    assert "project/config.json" in content and "workspace/code.py" in content
    assert f"agents/{p['agent_id']}/agent/config.json" in content
    assert f"agents/{helper['id']}/agent/crystals.jsonl" in content
    assert f"agents/{helper['id']}/workspace/ergebnis.md" in content
    assert {f"sessions/{chat_p}.json", f"sessions/{chat_h}.json"} <= content
    assert not any("auf-dem-nas" in n for n in content)
    info = meta(tgz)
    assert info["reason"] == "project_deleted" and info["extra"]["mounts_skipped"] == ["mounts/nas"]
    assert {m["username"] for m in info["extra"]["members"]} == {"testuser", "admin"}
    assert project_config.get(p["id"]) is None and not workspace_path(p["id"]).exists()
    assert not session_exists(chat_p) and not session_exists(chat_h)


def test_project_secrets_are_masked(archive_root) -> None:
    from hydrahive.projects import config as project_config
    p = make_project("Geheim B")
    project_config.update(p["id"], webhook_secret="WebhookGeheim-12345",
                          git_repos={"repo": {"url": "https://x", "git_token": "ghp_TokenGeheim1234567890"}})

    deletion.run("project", p["id"], "archive", actor="admin")

    cfg = read_member(only_package(archive_root, "projects"), "project/config.json")
    assert "WebhookGeheim" not in cfg and "TokenGeheim" not in cfg
    data = json.loads(cfg)
    assert data["webhook_secret"] == "***" and data["git_repos"]["repo"]["git_token"] == "***"
    assert data["git_repos"]["repo"]["url"] == "https://x"


def test_buddy_chat_in_project_survives(archive_root) -> None:
    """Ein Buddy-Chat (Master-Agent), der nur dem Projekt zugeordnet ist, gehört nicht zum Projekt."""
    from hydrahive.db import sessions
    p = make_project("Buddy C")
    buddy = make_agent("Buddy von testuser C", agent_type="master")
    sid = make_chat(buddy["id"], project_id=p["id"])

    deletion.run("project", p["id"], "permanent", actor="admin")

    assert session_exists(sid) and sessions.get(sid).project_id is None


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


def test_specialist_workspace_goes_with_internal_agent_delete() -> None:
    """Internes Löschen hinterlässt keine neuen Waisen mehr (Arbeitsordner kommt mit)."""
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._paths import workspace_for
    a = make_agent("Waise G")

    agent_config.delete(a["id"])

    assert not workspace_for(a).exists()


def test_permanent_project_leaves_no_package(archive_root) -> None:
    p = make_project("Weg H")
    deletion.run("project", p["id"], "permanent", actor="admin")
    assert packages(archive_root, "projects") == []
