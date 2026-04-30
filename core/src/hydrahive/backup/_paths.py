"""Welche Pfade gehen ins System-Backup, welche nicht.

Inkludiert: DB, alle User-Workspaces, alle Configs, Plugins, WhatsApp-State.
Exkludiert: VMs/Container (zu groß, separates Operator-Backup), transiente
Trigger-Dateien, Plugin-Hub-Cache.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.settings import settings


# Top-Level-Verzeichnisse die rein müssen (relativ zur tar-Wurzel als
# "data/<name>" bzw. "config/<name>").
def data_subdirs() -> list[tuple[str, Path]]:
    """Returns (tar-arcname, source-path) Paare für $HH_DATA_DIR-Inhalt."""
    return [
        ("data/agents", settings.agents_dir),
        ("data/projects", settings.projects_dir),
        ("data/plugins", settings.plugins_dir),
        ("data/whatsapp", settings.whatsapp_data_dir),
    ]


def config_dir_arcname() -> tuple[str, Path]:
    return ("config", settings.config_dir)


def db_arcname() -> tuple[str, Path]:
    """SQLite-DB wird via sqlite3.backup() in temp-File kopiert,
    dann unter diesem Namen ins Tar gehängt."""
    return ("db/sessions.db", settings.sessions_db)


# Pfade die NIE ins Backup dürfen:
# - VMs (mehrere GB qcow2-Files, separater Operator-Backup-Path)
# - .plugin-cache (transient, wird bei Bedarf neu geholt)
# - Trigger-Files (Self-Update, Restart, Voice-Install — laufen nur wenn frisch)
# - Auto-Rollback-Backups (sonst rekursive Aufblähung)
EXCLUDE_PATTERNS: tuple[str, ...] = (
    ".plugin-cache",
    ".update_request",
    ".restart_request",
    ".voice_install_request",
    ".backup-rollback-",
)


def is_excluded(path: Path) -> bool:
    name = path.name
    for pat in EXCLUDE_PATTERNS:
        if pat in name:
            return True
    return False
