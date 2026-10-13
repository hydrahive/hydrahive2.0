"""Projekt löschen: ein Paket mit allem, ohne Laufwerke (Spec archiv-system.md, Etappe 2)."""
from __future__ import annotations

import json

from hydrahive.archive import deletion
from tests._delete_fixtures import (
    make_agent, make_chat, make_project, meta, names, only_package, packages, read_member, session_exists,
)
from tests._delete_mounts import mount as _mount

pytest_plugins = ["tests._delete_env", "tests._delete_mounts"]  # Fixtures `archive_root`, `fake_mounts`


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


def test_share_comes_back_after_failure(archive_root, monkeypatch) -> None:
    """Sperren schaltet die Projekt-Freigabe aus; scheitert das Packen, ist sie danach wieder an."""
    from hydrahive.archive import package
    from hydrahive.samba import manager
    p = make_project("Freigabe I")
    shares: set[str] = {p["id"]}
    monkeypatch.setattr(manager, "is_share_enabled", lambda pid: pid in shares)
    monkeypatch.setattr(manager, "disable_share", lambda pid: (shares.discard(pid), (True, ""))[1])
    monkeypatch.setattr(manager, "enable_share", lambda pid, name: (shares.add(pid), (True, ""))[1])
    import hydrahive.samba as samba
    for fn in ("is_share_enabled", "disable_share", "enable_share"):
        monkeypatch.setattr(samba, fn, getattr(manager, fn))
    seen = []

    def boom(**kw):
        seen.append(p["id"] in shares)
        raise OSError("Platte voll")

    monkeypatch.setattr(package, "pack", boom)
    result = deletion.run("project", p["id"], "archive", actor="admin")

    assert result["error"] == "pack_failed" and seen == [False] and p["id"] in shares
