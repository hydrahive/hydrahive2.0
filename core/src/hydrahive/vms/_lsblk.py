"""lsblk sicher aufrufen – auch unter dem AppArmor-Profil, das Ubuntu 26.04 für lsblk mitbringt.

Befund 23.11.2026 (Neuinstallation Ubuntu 26.04.1): /etc/apparmor.d/lsblk (Paket apparmor, enforce) erlaubt lsblk
nur Konsole/Terminal und /dev/null als Ausgabe – nicht Dateien und nicht Sockets. Der Dienst läuft unter uvloop; dessen
create_subprocess_exec verbindet stdout über ein socketpair. lsblk schreibt dann still NICHTS (Exit 0, 0 Byte) –
/api/vms/host-disks meldete lsblk_parse_error. Eine echte Pipe (os.pipe) erlaubt das Profil (über abstractions/base
geerbte Deskriptoren aus pipe:), deshalb laufen alle lsblk-Aufrufe hier über subprocess.run in einem Thread.
Auf Systemen ohne dieses Profil (24.04, Debian, WSL ohne AppArmor) ändert sich nichts.
"""
from __future__ import annotations

import asyncio
import json
import subprocess

TIMEOUT = 10.0


class LsblkError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _run(args: list[str]) -> bytes:
    # subprocess.run nutzt os.pipe() für stdout – keine Sockets (siehe Modul-Doku).
    proc = subprocess.run(["lsblk", *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=TIMEOUT, check=False)
    return proc.stdout


async def lsblk_json(args: list[str]) -> dict:
    """``lsblk --json <args>`` als dict. Fehlercodes: lsblk_missing, lsblk_timeout, lsblk_empty, lsblk_parse_error."""
    try:
        out = await asyncio.to_thread(_run, ["--json", *args])
    except FileNotFoundError as e:
        raise LsblkError("lsblk_missing") from e
    except subprocess.TimeoutExpired as e:
        raise LsblkError("lsblk_timeout") from e
    if not out.strip():
        # Leere Ausgabe ist kein Parse-Fehler: lsblk durfte nicht schreiben (AppArmor) oder fand nichts.
        raise LsblkError("lsblk_empty")
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        raise LsblkError("lsblk_parse_error") from e
    if not isinstance(data, dict):
        raise LsblkError("lsblk_parse_error")
    return data
