"""Auto-Remount beim Backend-Start.

Nach einem Reboot sind alle CIFS-Mounts weg, aber in der DB stehen die
betroffenen Shares noch als 'mounted' (mit project_id). Diese Funktion zieht
sie einmalig wieder hoch. Kein Loop — ein Reboot ist ein diskretes Ereignis,
und ein Dauer-Loop würde nur unnötig gegen den Fileserver pollen.
"""
from __future__ import annotations

import logging

from hydrahive.db.connection import db
from hydrahive.smbmounts import db as mounts_db
from hydrahive.smbmounts import mounter

logger = logging.getLogger(__name__)


def reconcile_mounts_on_start() -> None:
    """Stellt zugewiesene Shares wieder her, die faktisch nicht (mehr) gemountet
    sind. Idempotent: bereits aktive Mounts werden uebersprungen.
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT mount_id FROM smb_mounts WHERE project_id IS NOT NULL "
            "AND mount_state IN ('mounted', 'mounting', 'error')"
        ).fetchall()

    if not rows:
        return

    restored = 0
    failed = 0
    for row in rows:
        m = mounts_db.get_mount(row["mount_id"])
        if not m or not m.project_id:
            continue
        mp = mounter.mountpoint_for(m.project_id, m.name)
        if mounter.is_mounted(mp):
            mounts_db.set_state(m.mount_id, "mounted")
            continue
        ok, result = mounter.mount(m)
        if ok:
            mounts_db.set_state(m.mount_id, "mounted")
            restored += 1
        else:
            mounts_db.set_state(m.mount_id, "error", error_code=result)
            failed += 1
            logger.warning(
                "SMB-Auto-Remount fehlgeschlagen: %s (%s) -> %s",
                m.name, mp, result,
            )

    if restored or failed:
        logger.info(
            "SMB-Auto-Remount: %d wiederhergestellt, %d fehlgeschlagen",
            restored, failed,
        )
