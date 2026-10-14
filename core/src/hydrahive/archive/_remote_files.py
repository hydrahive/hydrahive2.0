"""Hilfen der Kopier-Reihe (Spec archiv-system.md, Etappe 3): Stand je Paket in seiner .json, welche
Dateien aufs NAS gehören, sha256 eines Pakets. Ausgelagert aus remote_sync.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from hydrahive.archive._paths import TRASH_DIR, archive_root


def meta_path(rel: str) -> Path:
    return archive_root() / (rel + ".json")


def set_remote(rel: str, **remote) -> None:
    """Stand in die .json eines Pakets schreiben (von Hand abgelegte Dateien haben keine)."""
    mp = meta_path(rel)
    try:
        meta = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    meta["remote"] = remote
    tmp = mp.with_name(mp.name + ".part")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, mp)


def files():
    """Alles, was aufs NAS gehört: Pakete (ohne ihre .json) und von Hand abgelegte Dateien."""
    root = archive_root()
    for dirpath, dirs, files in os.walk(root, followlinks=False):
        here = Path(dirpath)
        dirs[:] = [d for d in dirs if not d.startswith(".") and not (here == root and d == TRASH_DIR)]
        for f in files:
            if f.startswith(".") or f.endswith((".part", ".tar.gz.json", ".tmp")) or here == root:
                continue
            yield str((here / f).relative_to(root)).replace(os.sep, "/")


def sha_local(rel: str) -> str:
    try:
        sha = json.loads(meta_path(rel).read_text(encoding="utf-8")).get("sha256")
        if sha:
            return sha
    except (OSError, ValueError):
        pass
    h = hashlib.sha256()
    with open(archive_root() / rel, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()
