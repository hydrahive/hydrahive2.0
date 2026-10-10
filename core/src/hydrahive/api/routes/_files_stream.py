"""/api/files: Datei sicher öffnen und aus dem GEÖFFNETEN Handle ausliefern (Folge-Review #539, TOCTOU).

Vorher: Pfad prüfen, dann ``FileResponse(pfad)`` – die Datei wird erst beim Senden per Name geöffnet. Wer im eigenen
Workspace schreiben darf, konnte sie dazwischen gegen einen Symlink auf eine fremde Datei tauschen.
Jetzt: öffnen (O_NOFOLLOW für die letzte Stelle), den echten Ort am Handle bestimmen (``/proc/self/fd``), DAS prüfen
und aus genau diesem Handle senden – auch bei Range-Anfragen (Video/Audio-Spulen).
"""
from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterator
from pathlib import Path

from fastapi import Request, status
from fastapi.responses import Response, StreamingResponse

from hydrahive.api.middleware.errors import coded

CHUNK = 64 * 1024


def open_checked(path: Path, check: Callable[[Path], None]) -> tuple[int, os.stat_result]:
    """Öffnet ``path`` und ruft ``check`` mit dem ECHTEN Ort der geöffneten Datei auf. Gibt (fd, stat) zurück."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
    except (FileNotFoundError, NotADirectoryError):
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found") from None
    except OSError:                    # u. a. ELOOP: letzter Teil ist (inzwischen) ein Symlink
        raise coded(status.HTTP_403_FORBIDDEN, "path_not_allowed") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
        check(Path(os.readlink(f"/proc/self/fd/{fd}")))
        return fd, st
    except BaseException:
        os.close(fd)
        raise


def _range(header: str | None, size: int) -> tuple[int, int] | None:
    """Ein einzelner Bereich „bytes=a-b“, „bytes=a-“ oder „bytes=-n“ → (start, ende exkl.). Sonst None = ganze Datei
    (auch mehrere Bereiche „a-b,c-d“: die scheitern am Zahlenlesen)."""
    if not header or not header.startswith("bytes="):
        return None
    a, _, b = header[6:].strip().partition("-")
    try:
        if a == "":
            n = int(b)
            return (max(0, size - n), size) if n > 0 else None
        start = int(a)
        end = int(b) + 1 if b else size
    except ValueError:
        return None
    if start >= size or end <= start:
        raise coded(status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, "range_not_satisfiable")
    return start, min(end, size)


def _chunks(fd: int, start: int, end: int) -> Iterator[bytes]:
    try:
        os.lseek(fd, start, os.SEEK_SET)
        left = end - start
        while left > 0:
            chunk = os.read(fd, min(CHUNK, left))
            if not chunk:
                break
            left -= len(chunk)
            yield chunk
    finally:
        os.close(fd)


def send_fd(fd: int, st: os.stat_result, media_type: str, request: Request) -> Response:
    """Antwort aus dem offenen Handle (nur GET – die Route kennt kein HEAD); schließt es am Ende, auch bei Abbruch."""
    size = st.st_size
    try:
        span = _range(request.headers.get("range"), size)
    except BaseException:
        os.close(fd)
        raise
    start, end = span or (0, size)
    headers = {"accept-ranges": "bytes", "content-length": str(end - start)}
    if span:
        headers["content-range"] = f"bytes {start}-{end - 1}/{size}"
    return StreamingResponse(_chunks(fd, start, end), status_code=206 if span else 200, headers=headers,
                             media_type=media_type)
