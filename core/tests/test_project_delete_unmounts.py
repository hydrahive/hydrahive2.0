"""Projekt-Löschen muss zugewiesene SMB-Mounts aushängen + freigeben."""
from __future__ import annotations


def test_delete_clears_mount_assignment(setup_test_env):
    from hydrahive.db.connection import init_db
    from hydrahive.projects import config as project_config
    from hydrahive.smbmounts import db as mounts_db

    init_db()  # Migrations anwenden (sonst keine smb_mounts-Tabelle)

    proj = project_config.create(
        name="delmount", llm_model="anthropic/claude-sonnet-4",
        created_by="testuser", members=["testuser"],
    )
    pid = proj["id"]

    m = mounts_db.create_mount(
        owner="testuser", name="delnas", host="10.255.255.1", share="backups",
    )
    # direkt zuweisen (ohne echten Mount) + state setzen
    mounts_db.set_project(m.mount_id, pid)
    mounts_db.set_state(m.mount_id, "mounted")
    assert mounts_db.get_mount(m.mount_id).project_id == pid

    # Projekt löschen → Mount muss freigegeben + unmounted sein
    assert project_config.delete(pid) is True

    after = mounts_db.get_mount(m.mount_id)
    assert after is not None                 # Mount-Definition bleibt erhalten
    assert after.project_id is None          # Zuweisung weg
    assert after.mount_state == "unmounted"
