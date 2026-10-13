"""Datei-Hilfen für den Archiv-Umzug (archive/move.py): auflisten, kopieren, prüfen, zurückrollen, aufräumen."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


def _free_bytes(path: Path) -> int:
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def _files(root: Path) -> list[str]:
    out = []
    for dirpath, _dirs, files in os.walk(root, followlinks=False):
        out += [str((Path(dirpath) / f).relative_to(root)) for f in files]
    return sorted(out)


def _inside(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve() or b.resolve() in a.resolve().parents


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        os.symlink(os.readlink(src), dst)
    else:
        shutil.copy2(src, dst)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(source: Path, target: Path, files: list[str]) -> bool:
    for rel in files:
        s, t = source / rel, target / rel
        if s.is_symlink():
            if not t.is_symlink() or os.readlink(s) != os.readlink(t):
                return False
            continue
        if not t.is_file() or t.stat().st_size != s.stat().st_size:
            return False
        meta = s.with_name(s.name + ".json")
        if rel.endswith(".tar.gz") and meta.is_file():
            try:
                want = json.loads(meta.read_text()).get("sha256")
            except ValueError:
                want = None
            if want and _sha256(t) != want:
                return False
    return True


def _rollback(target: Path, copied: list[str]) -> None:
    for rel in reversed(copied):
        (target / rel).unlink(missing_ok=True)
    for dirpath, _dirs, _files in sorted(os.walk(target), key=lambda x: -len(x[0])):
        try:
            os.rmdir(dirpath)
        except OSError:
            pass


def _cleanup(source: Path, copied: list[str]) -> list[str]:
    for rel in copied:
        (source / rel).unlink(missing_ok=True)
    left = _files(source) if source.is_dir() else []
    if not left:
        shutil.rmtree(source, ignore_errors=True)
    return left
