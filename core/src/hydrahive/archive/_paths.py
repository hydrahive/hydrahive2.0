"""Pfade im System-Archiv. Alles liegt unter archive_root(); nichts darf hinaus."""
from __future__ import annotations

from pathlib import Path

from hydrahive.archive import location

# Feste Arten. `kind` wird zum Ordnernamen – deshalb nur aus dieser Liste.
KINDS: tuple[str, ...] = ("agents", "projects", "users", "backups", "uploads")
TRASH_DIR = ".papierkorb"   # Samba-Papierkorb (recycle:repository), siehe archive/share.py


def archive_root() -> Path:
    # Immer über location – so gilt eine Änderung des Orts sofort überall.
    return location.archive_root()


def kind_dir(kind: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"Unbekannte Archiv-Art: {kind!r}")
    return archive_root() / kind


def trash_dir() -> Path:
    return archive_root() / TRASH_DIR


def inside_root(path: Path) -> bool:
    """True, wenn `path` (ohne Symlinks aufzulösen) unter archive_root() liegt."""
    root = archive_root().resolve()
    try:
        Path(path).absolute().relative_to(root)
    except ValueError:
        return False
    return True
