"""Begrenzte, geschwärzte Ausgabe von Modul-Extension-Skripten."""
from __future__ import annotations

import subprocess
from collections import deque
from collections.abc import Iterator
from pathlib import Path

from hydrahive.credentials import redaction

_MAX_LINES = 500
_MAX_LINE_CHARS = 2_000
_READ_CHARS = 4_096
_ERROR_TAIL_LINES = 8
_ERROR_MAX_CHARS = 4_000


class ServiceScriptError(RuntimeError):
    """Ein Extension-Skript ist fehlgeschlagen; der Text ist bereits bereinigt."""


def _output_line(raw: str, secrets: set[str]) -> str:
    """Eine Scriptzeile begrenzen und bekannte sowie typische Secrets schwärzen."""
    line = raw.strip()
    if len(line) > _MAX_LINE_CHARS:
        line = line[:_MAX_LINE_CHARS] + "…"
    return redaction.redact_detected(redaction.scrub(line, secrets))


def _error_detail(tail: deque[str]) -> str:
    detail = " | ".join(tail) or "keine Script-Ausgabe"
    if len(detail) > _ERROR_MAX_CHARS:
        return "…" + detail[-(_ERROR_MAX_CHARS - 1):]
    return detail


def run(path: Path, module_id: str, script: str) -> Iterator[str]:
    """Skript ohne Shell starten und dessen bereinigte Ausgabe weiterreichen.

    stdout und stderr werden zusammengeführt, damit die zeitliche Reihenfolge
    verständlich bleibt. Feste Lese- und Ausgabelimits schützen den SSE-Stream
    vor Fortschrittsfluten; der Fehler-Tail läuft trotzdem bis zum Prozessende.
    """
    if not path.exists():
        return
    secrets = redaction.secret_values()
    tail: deque[str] = deque(maxlen=_ERROR_TAIL_LINES)
    emitted = 0
    truncated = False
    process = subprocess.Popen(
        ["bash", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    while True:
        raw = process.stdout.readline(_READ_CHARS)
        if raw == "":
            break
        # Incus, curl und apt nutzen teils CR-Fortschritt ohne neue Zeile.
        for part in raw.replace("\r", "\n").split("\n"):
            line = _output_line(part, secrets)
            if not line:
                continue
            tail.append(line)
            if emitted < _MAX_LINES:
                emitted += 1
                yield line
            elif not truncated:
                truncated = True
                yield "[modules] Script-Ausgabe gekürzt"
    returncode = process.wait()
    if returncode != 0:
        raise ServiceScriptError(
            f"extension_script_failed: {module_id}/{script}, exit {returncode}: {_error_detail(tail)}"
        )
