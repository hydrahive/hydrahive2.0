"""Samba-Share-Management für Projekt-Workspaces.

MVP (Option A): ein gemeinsamer Samba-User (settings.samba_user) für alle
freigegebenen Projekte. Pro Projekt ein Toggle, Share-Pfad ist der Workspace.

Per Projekt eine Config-Datei in settings.samba_includes_dir/<project_id>.conf,
smbd reload via subprocess. Bei späterem Per-User-Auth-Refactor (Issue: TBD)
muss nur die Render-Funktion in `manager.py::render_share()` umgebaut werden.
"""
from hydrahive.samba.manager import (
    disable_share,
    enable_share,
    is_share_enabled,
    samba_status,
)

__all__ = ["disable_share", "enable_share", "is_share_enabled", "samba_status"]
