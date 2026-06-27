"""SMB-Mount-Datentypen — Dataclass für Persistenz und API-Antworten.

Eine SMB/CIFS-Freigabe auf einem externen Fileserver, die einem Projekt
zugewiesen und in dessen Workspace gemountet werden kann.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MountState = Literal["unmounted", "mounting", "mounted", "error"]

# Name wird zum Mount-Ordnernamen → strikt, kein Pfad-Metazeichen.
NAME_RE = r"^[a-zA-Z][a-zA-Z0-9_-]{0,31}$"  # 1-32 chars
# Host: Hostname oder IP, keine Whitespaces/Slashes/Shell-Metazeichen.
HOST_RE = r"^[a-zA-Z0-9._-]{1,253}$"
# Share-Name: keine Slashes/Backslashes/Whitespaces.
SHARE_RE = r"^[a-zA-Z0-9._$ -]{1,80}$"
# Subpath: relativer Pfad ohne '..' (server-seitig zusätzlich geprüft).
SUBPATH_RE = r"^[a-zA-Z0-9._/ -]{0,255}$"

# Erlaubte mount.cifs-Optionen (Whitelist). Alles andere wird verworfen.
ALLOWED_OPTIONS: frozenset[str] = frozenset(
    {"vers", "iocharset", "file_mode", "dir_mode", "uid", "gid", "nobrl", "cache"}
)


@dataclass
class SmbMount:
    mount_id: str
    owner: str
    name: str
    host: str
    share: str
    created_at: str
    updated_at: str
    subpath: str | None = None
    credential: str | None = None
    read_only: bool = False
    options: str | None = None
    project_id: str | None = None
    mount_state: MountState = "unmounted"
    last_error_code: str | None = None
