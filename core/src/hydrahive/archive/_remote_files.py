"""Hilfen der Kopier-Reihe (Spec archiv-system.md, Etappe 3): Stand je Paket in seiner .json, welche
Dateien aufs NAS gehören, sha256 eines Pakets. Ausgelagert aus remote_sync.py.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from hydrahive.archive._paths import TRASH_DIR, archive_root
from hydrahive.settings import settings

MANUAL_STATE = "archive-remote-manual.json"   # Stand der von Hand abgelegten Dateien (die haben keine .json)


def meta_path(rel: str) -> Path:
    return archive_root() / (rel + ".json")


def _manual_path() -> Path:
    return Path(settings.config_dir) / MANUAL_STATE


def manual_states() -> dict[str, dict]:
    try:
        data = json.loads(_manual_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _set_manual(rel: str, remote: dict) -> None:
    data = manual_states()
    data[rel] = {**remote, "size": (archive_root() / rel).stat().st_size}
    p = _manual_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def remote_of(rel: str) -> dict:
    """Stand der Kopie auf dem Server – aus der .json des Pakets bzw. der Liste für von Hand Abgelegtes.
    Bei von Hand abgelegten Dateien gilt der Stand nur, solange sich die Größe nicht geändert hat."""
    try:
        return json.loads(meta_path(rel).read_text(encoding="utf-8")).get("remote") or {}
    except (OSError, ValueError):
        pass
    st = manual_states().get(rel) or {}
    try:
        same = st.get("size") == (archive_root() / rel).stat().st_size
    except OSError:
        return {}
    return {k: v for k, v in st.items() if k != "size"} if same else {}


def set_remote(rel: str, **remote) -> None:
    """Stand in die .json eines Pakets schreiben – bzw. in die Liste, wenn es keine .json gibt (von Hand)."""
    mp = meta_path(rel)
    try:
        meta = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        if (archive_root() / rel).is_file():
            _set_manual(rel, remote)
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
