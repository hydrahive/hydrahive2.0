"""Datei-Zugriff der Werkzeuge file_read/file_write/file_patch – auf dem Server oder im Projekt-Container
(docs/specs/projekt-container-ausfuehrung.md, K1b).

Container: Pfade werden IM Container aufgelöst (`realpath`), damit dortige Symlinks zählen, und müssen unter dem
Arbeitsverzeichnis liegen. Lesen über `cat`, Schreiben über `install` mit Daten auf stdin – immer als Projekt-Nutzer,
nie als root, Pfade immer als eigenes Argument (nie in einen Shell-Text eingesetzt). Die Host-Platte wird nie berührt.
"""
from __future__ import annotations

import asyncio
import posixpath
import shutil

from hydrahive.tools._launcher_container import ExecutionUnavailable, launcher_for
from hydrahive.tools._path import PathOutsideWorkspace

MAX_READ_BYTES = 10 * 1024 * 1024
_INCUS = shutil.which("incus") or "incus"
# Elternordner anlegen und Datei atomar ersetzen; Ziel kommt als $1, Daten auf stdin.
_WRITE = 'd=$(dirname "$1") && mkdir -p "$d" && t=$(mktemp "$d/.hh-write.XXXXXX") && cat > "$t" && ' \
         'chmod 0644 "$t" && mv -f "$t" "$1"'


class ContainerFsError(RuntimeError):
    pass


def _execution(ctx) -> dict:
    """Ausführung des Projekts; wirft ExecutionUnavailable statt still auf den Server zu fallen."""
    from hydrahive.tools._launcher_container import ContainerLauncher
    lc = launcher_for(ctx)
    if isinstance(lc, ContainerLauncher):
        return {"mode": "container", "container": lc.container, "workdir": lc.workdir, "user": lc.user}
    return {"mode": "host"}


async def _incus(args: list[str], stdin: bytes | None) -> tuple[int, bytes, bytes]:
    p = await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env={"PATH": "/usr/bin:/bin"})
    out, err = await asyncio.wait_for(p.communicate(stdin), timeout=60)
    return p.returncode or 0, out, err


def _exec(ex: dict, *cmd: str) -> list[str]:
    return [_INCUS, "exec", ex["container"], "--user", str(ex["user"]), "--group", str(ex["user"]),
            "--cwd", ex["workdir"], "--", *cmd]


def _inside(ex: dict, resolved: str) -> bool:
    wd = ex["workdir"].rstrip("/")
    return resolved == wd or resolved.startswith(wd + "/")


async def resolve(ex: dict, requested: str, *, must_exist: bool) -> str:
    if not requested:
        raise PathOutsideWorkspace("Leerer Pfad")
    p = requested if requested.startswith("/") else posixpath.join(ex["workdir"], requested)
    rc, out, _ = await _incus(_exec(ex, "realpath", "-e" if must_exist else "-m", "--", p), None)
    resolved = out.decode(errors="replace").strip()
    if rc != 0 or not resolved:
        if must_exist:
            raise FileNotFoundError(requested)
        raise PathOutsideWorkspace(f"Pfad nicht auflösbar: {requested}")
    if not _inside(ex, resolved):
        raise PathOutsideWorkspace(f"Pfad außerhalb des Arbeitsverzeichnisses: {requested}")
    return resolved


async def read_bytes(ex: dict, path: str) -> bytes:
    rc, out, err = await _incus(_exec(ex, "cat", "--", path), None)
    if rc != 0:
        raise ContainerFsError(err.decode(errors="replace")[:200] or "Lesefehler")
    if len(out) > MAX_READ_BYTES:
        raise ContainerFsError("Datei zu groß")
    return out


async def write_bytes(ex: dict, path: str, data: bytes) -> None:
    rc, _, err = await _incus(_exec(ex, "sh", "-c", _WRITE, "hh-write", path), data)
    if rc != 0:
        raise ContainerFsError(err.decode(errors="replace")[:200] or "Schreibfehler")


__all__ = ["ExecutionUnavailable", "ContainerFsError", "MAX_READ_BYTES", "resolve", "read_bytes", "write_bytes"]
