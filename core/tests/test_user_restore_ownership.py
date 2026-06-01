"""User-Restore darf keine fremden Agents/Projects überschreiben (Issue #183).

Der Manifest-username-Check ist angreifer-setzbar; die echte Tenant-Grenze ist
die DB-Ownership pro Agent-/Projekt-ID. Restore gated jetzt pro Entität.
"""
from __future__ import annotations

import io
import json
import tarfile


def _make_user_archive(path, *, username, agents=None, projects=None):
    with tarfile.open(path, "w:gz") as tar:
        mani = json.dumps({"kind": "user", "username": username}).encode()
        mi = tarfile.TarInfo("manifest.json")
        mi.size = len(mani)
        tar.addfile(mi, io.BytesIO(mani))
        for aid, cfg in (agents or {}).items():
            b = json.dumps(cfg).encode()
            ti = tarfile.TarInfo(f"agents/{aid}/config.json")
            ti.size = len(b)
            tar.addfile(ti, io.BytesIO(b))
        for pid, cfg in (projects or {}).items():
            b = json.dumps(cfg).encode()
            ti = tarfile.TarInfo(f"projects/{pid}/config.json")
            ti.size = len(b)
            tar.addfile(ti, io.BytesIO(b))


def _write_agent(settings, agent_id, owner, name):
    d = settings.agents_dir / agent_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps(
        {"id": agent_id, "owner": owner, "type": "specialist", "name": name}))


def test_restore_does_not_overwrite_foreign_agent(client, tmp_path):
    from hydrahive.backup import user_restore
    from hydrahive.settings import settings

    _write_agent(settings, "foreign-agent", owner="victim", name="V")

    arc = tmp_path / "u.tar.gz"
    _make_user_archive(arc, username="attacker", agents={
        "foreign-agent": {"id": "foreign-agent", "owner": "attacker", "type": "specialist", "name": "PWNED"},
        "own-agent": {"id": "own-agent", "owner": "attacker", "type": "specialist", "name": "Mine"},
    })
    user_restore.restore_user_archive(arc, "attacker")

    foreign = json.loads((settings.agents_dir / "foreign-agent" / "config.json").read_text())
    assert foreign["owner"] == "victim"
    assert foreign["name"] == "V", "fremder Agent darf nicht überschrieben werden"

    own = settings.agents_dir / "own-agent" / "config.json"
    assert own.exists(), "eigener Agent muss wiederhergestellt werden"
    assert json.loads(own.read_text())["owner"] == "attacker"


def test_restore_skips_new_agent_claiming_foreign_owner(client, tmp_path):
    from hydrahive.backup import user_restore
    from hydrahive.settings import settings

    arc = tmp_path / "u2.tar.gz"
    _make_user_archive(arc, username="attacker", agents={
        "ghost": {"id": "ghost", "owner": "victim", "type": "specialist", "name": "G"},
    })
    user_restore.restore_user_archive(arc, "attacker")

    assert not (settings.agents_dir / "ghost").exists(), \
        "neuer Agent mit fremdem Owner darf nicht angelegt werden"


def test_restore_does_not_overwrite_foreign_project(client, tmp_path):
    from hydrahive.backup import user_restore
    from hydrahive.settings import settings

    pdir = settings.projects_dir / "foreign-proj"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "config.json").write_text(json.dumps(
        {"id": "foreign-proj", "created_by": "victim", "name": "VP"}))

    arc = tmp_path / "u3.tar.gz"
    _make_user_archive(arc, username="attacker", projects={
        "foreign-proj": {"id": "foreign-proj", "created_by": "attacker", "name": "PWNED"},
    })
    user_restore.restore_user_archive(arc, "attacker")

    foreign = json.loads((pdir / "config.json").read_text())
    assert foreign["created_by"] == "victim"
    assert foreign["name"] == "VP", "fremdes Projekt darf nicht überschrieben werden"
