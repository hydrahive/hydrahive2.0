"""Auto-Remount-Reconcile beim Start.

Ohne echten Fileserver: ein als 'mounted' markierter, aber faktisch nicht
gemounteter Share (Reboot-Zustand) wird via mounter.mount() angefasst.
mount() schlägt gegen den toten Host fehl → state wird 'error' (sauber, kein
Crash). Verifiziert wird der Reconcile-Durchlauf + State-Übergang.
"""
from __future__ import annotations


def test_reconcile_attempts_remount_of_assigned(setup_test_env):
    from hydrahive.db.connection import init_db
    from hydrahive.projects import config as project_config
    from hydrahive.smbmounts import db as mounts_db
    from hydrahive.smbmounts.reconcile import reconcile_mounts_on_start

    init_db()
    proj = project_config.create(
        name="reconc", llm_model="anthropic/claude-sonnet-4",
        created_by="testuser", members=["testuser"],
    )
    m = mounts_db.create_mount(
        owner="testuser", name="reconcnas", host="10.255.255.1", share="backups",
    )
    # Reboot-Zustand simulieren: zugewiesen + DB sagt 'mounted', faktisch nicht.
    mounts_db.set_project(m.mount_id, proj["id"])
    mounts_db.set_state(m.mount_id, "mounted")

    reconcile_mounts_on_start()

    after = mounts_db.get_mount(m.mount_id)
    # toter host -> remount scheitert -> state error, fehlercode gesetzt
    assert after.mount_state == "error"
    assert after.last_error_code
    # zuweisung bleibt erhalten (nur der mount-versuch ist fehlgeschlagen)
    assert after.project_id == proj["id"]


def test_reconcile_noop_when_nothing_assigned(setup_test_env):
    from hydrahive.db.connection import init_db
    from hydrahive.smbmounts.reconcile import reconcile_mounts_on_start

    init_db()
    # darf ohne zugewiesene mounts einfach sauber durchlaufen
    reconcile_mounts_on_start()
