"""Projekt löschen – direkt, ohne Archiv (internes Aufräumen, z. B. Storyteller `drop_project`).

Fehler 1 (Spec archiv-system.md, Etappe 2): Früher lief `shutil.rmtree` auch dann, wenn das
Aushängen eines Netzlaufwerks gescheitert war – und löschte Dateien auf dem Fileserver.
Jetzt: erst alle Laufwerke aushängen und prüfen. Hängt danach noch eines von HydraHive,
wird gar nichts gelöscht (`ProjectDeleteBlocked`). Gelöscht wird nur mit `remove_tree`, das
nie in ein eingehängtes Laufwerk geht (auch nicht in ein von Hand eingehängtes).
"""
from __future__ import annotations

import logging
import os

from hydrahive.agents import config as agent_config
from hydrahive.projects import _members_model
from hydrahive.projects._config_io import get
from hydrahive.projects._paths import project_dir, workspace_path

logger = logging.getLogger(__name__)


class ProjectDeleteBlocked(RuntimeError):
    """Ein Netzlaufwerk im Projekt ließ sich nicht aushängen – es wurde nichts gelöscht."""

    def __init__(self, mounts: list[str]) -> None:
        super().__init__(f"Laufwerk hängt noch: {', '.join(mounts)}")
        self.mounts = mounts


def unmount_all(project_id: str) -> list[str]:
    """Hängt alle Laufwerke des Projekts aus. Gibt zurück, was danach NOCH hängt (leer = gut).

    Meldet umount „ok“, hängt das Laufwerk aber noch, zählt es als gescheitert."""
    from hydrahive.smbmounts import db as mounts_db
    from hydrahive.smbmounts import mounter
    stuck = []
    for m in mounts_db.list_for_project(project_id):
        mp = mounter.mountpoint_for(project_id, m.name)
        ok, code = mounter.umount(m)
        if not ok or os.path.ismount(mp):
            logger.warning("Projekt %s: Laufwerk %s nicht ausgehängt (%s)", project_id, mp, code if not ok else "busy")
            stuck.append(mp)
        else:
            mounts_db.set_state(m.mount_id, "unmounted")
    return stuck


def delete(project_id: str) -> bool:
    cfg = get(project_id)
    if not cfg:
        return False
    stuck = unmount_all(project_id)
    if stuck:
        raise ProjectDeleteBlocked(stuck)
    if cfg.get("agent_id"):
        agent_config.delete(cfg["agent_id"])
    for agent in agent_config.list_all():   # create_specialist, Storyteller-Helfer – sonst verwaist
        if agent.get("project_id") == project_id and agent.get("id") != cfg.get("agent_id"):
            agent_config.delete(agent["id"])
    remove_rest(project_id, cfg)
    return True


def remove_rest(project_id: str, cfg: dict) -> list[str]:
    """Zuordnungen lösen, Freigabe aus, Ordner weg. Wiederholbar. Gibt stehengebliebene Laufwerke zurück."""
    from hydrahive.agents._workspace_links import sync_links_for_user
    from hydrahive.archive.safe_rm import remove_tree
    from hydrahive.containers import db as containers_db
    from hydrahive.projects._linked import sync_pointing_to
    from hydrahive.samba import disable_share as samba_disable
    from hydrahive.smbmounts import db as mounts_db
    from hydrahive.vms import db as vms_db
    affected_users = set(_members_model.usernames(cfg))
    if cfg.get("created_by"):
        affected_users.add(cfg["created_by"])
    vms_db.clear_project_assignments(project_id)          # VMs/Container bleiben, project_id wird NULL
    containers_db.clear_project_assignments(project_id)
    mounts_db.clear_project_assignments(project_id)
    samba_disable(project_id)
    kept = remove_tree(workspace_path(project_id))
    remove_tree(project_dir(project_id))
    for user in affected_users:
        sync_links_for_user(user)
    sync_pointing_to(project_id)                # verwaiste linked/<Name> anderer Projekte entfernen
    logger.info("Projekt gelöscht: %s", project_id)
    return kept
