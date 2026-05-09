from __future__ import annotations

import logging
import os
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

# 02775 = setgid + rwxrwxr-x. Setgid sorgt dafür dass alle neuen Sub-Dirs
# die parent-Group erben (= hydrahive). Group-rwx erlaubt dem Samba-User
# (Mitglied der hydrahive-Gruppe per usermod im 47-samba.sh) Schreibzugriff
# auf den Workspace via Samba-Share. Ohne setgid würden tief geschachtelte
# Sub-Dirs die default-Group des Erzeugers übernehmen statt hydrahive.
WORKSPACE_DIR_MODE = 0o2775


def projects_root() -> Path:
    return settings.data_dir / "projects"


def project_dir(project_id: str) -> Path:
    return projects_root() / project_id


def config_path(project_id: str) -> Path:
    return project_dir(project_id) / "config.json"


def workspace_path(project_id: str) -> Path:
    return settings.data_dir / "workspaces" / "projects" / project_id


def ensure_workspace(project_id: str) -> Path:
    p = workspace_path(project_id)
    p.mkdir(parents=True, exist_ok=True)
    # Setgid + group-rwx setzen — auch idempotent für bereits existierende
    # Workspaces (wenn die noch ohne Mode angelegt wurden).
    try:
        if p.stat().st_mode & 0o7777 != WORKSPACE_DIR_MODE:
            os.chmod(p, WORKSPACE_DIR_MODE)
    except OSError as e:
        # Kein hartes fail — wenn der hydrahive-User keine chmod-Permission
        # hat (z.B. Workspace gehört einem anderen User), läuft das System
        # weiter, nur Samba-Schreibzugriff kann brechen.
        logger.warning("ensure_workspace(%s): chmod fehlgeschlagen: %s",
                       project_id, e)
    return p.resolve()
