"""Welche Pfade gehen ins System-Backup, welche nicht.

Inkludiert: DB, alle User-Workspaces (workspaces/), Module (modules/),
Projekt-Metadaten, Agents, Configs, Plugins, WhatsApp-State.
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
        # workspaces/ enthält die ECHTEN Projekt-/Agent-Daten (Git-Repos, Code) —
        # data/projects trägt nur config.json-Metadaten. Ohne diesen Eintrag ging
        # bei jedem System-Backup die eigentliche Arbeit verloren.
        ("data/workspaces", settings.workspaces_dir),
        # modules/ = installierte Feature-Module (Backend+Frontend).
        ("data/modules", settings.modules_dir),
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
    ".qcow2",            # VM-Disk-Images (mehrere GB) — nie ins System-Backup
    ".plugin-cache",
    ".update_request",
    ".restart_request",
    ".voice_install_request",
    ".backup-rollback-",
    ".hh2-restore-",     # transientes Extraktions-Tempdir (Restore läuft in data_dir)
)

# Verzeichnis-Namen die komplett ausgeklammert werden (vergleicht gegen Path-Parts).
# - tls/: Private-Key ist nur für root lesbar; Cert ist Server-spezifisch (IP/Hostname),
#   beim Migrate macht es mehr Sinn neu zu generieren als alten Cert mitzunehmen.
EXCLUDE_DIRS: tuple[str, ...] = (
    "tls",
    "vms",               # VM-/Container-Disks (mehrere GB, separater Operator-Backup)
    ".module-cache",     # transienter Modul-Hub-Cache
)


def is_excluded(path: Path) -> bool:
    parts = path.parts
    # Pattern-Match auf JEDEM Path-Teil — fängt sowohl die Top-Level-Datei
    # ".update_request" als auch eine Datei UNTER ".plugin-cache/" ab.
    for part in parts:
        for pat in EXCLUDE_PATTERNS:
            if pat in part:
                return True
    for d in EXCLUDE_DIRS:
        if d in parts:
            return True
    return False
