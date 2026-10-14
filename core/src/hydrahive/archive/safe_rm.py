"""Löschen, ohne je in ein eingehängtes Laufwerk zu gehen (Fehler 1, Spec archiv-system.md, Etappe 2).

`shutil.rmtree` beachtet keine Laufwerksgrenzen: Ein noch eingehängtes NAS unter
`workspaces/projects/<id>/mounts/nas` würde mitgelöscht. Hier wird jeder Ordner
vorher mit `os.path.ismount` geprüft. Ein Laufwerk bleibt samt Elternordnern
stehen und wird gemeldet – auch eines, das HydraHive nicht kennt (von Hand
eingehängt, USB).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def mounts_below(root: Path) -> list[str]:
    """Alle eingehängten Laufwerke unter `root` (ohne hineinzugehen)."""
    found: list[str] = []
    if not os.path.isdir(root) or os.path.islink(root):
        return found
    for dirpath, dirs, _files in os.walk(root, followlinks=False):
        keep = []
        for d in dirs:
            p = os.path.join(dirpath, d)
            if os.path.islink(p):
                continue
            if os.path.ismount(p):
                found.append(p)
            else:
                keep.append(d)
        dirs[:] = keep
    return sorted(found)


def remove_tree(root: Path) -> list[str]:
    """Löscht `root` vollständig, außer eingehängten Laufwerken.

    Gibt die stehengebliebenen Laufwerke zurück (leer = alles weg). Symlinks
    werden als Link entfernt, nie verfolgt. Ist `root` selbst ein Laufwerk,
    passiert nichts.
    """
    root = Path(root)
    if os.path.islink(root):
        root.unlink()
        return []
    if not root.exists():
        return []
    if os.path.ismount(root):
        logger.warning("Löschen übersprungen, %s ist ein eingehängtes Laufwerk", root)
        return [str(root)]
    kept: list[str] = []
    _remove(root, kept)
    if kept:
        logger.warning("Eingehängte Laufwerke stehen gelassen: %s", ", ".join(kept))
    return sorted(kept)


def _remove(path: Path, kept: list[str]) -> bool:
    """True, wenn `path` ganz weg ist."""
    empty = True
    with os.scandir(path) as it:
        entries = list(it)
    for entry in entries:
        p = Path(entry.path)
        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
            p.unlink()
            continue
        if os.path.ismount(p):
            kept.append(str(p))
            empty = False
            continue
        if not _remove(p, kept):
            empty = False
    if empty:
        path.rmdir()
    return empty
