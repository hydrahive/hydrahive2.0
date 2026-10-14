"""Zugriff auf den externen Server per SMB, ohne Einhängen (Spec archiv-system.md, Etappe 3).

Python-Bibliothek smbprotocol: kein root, kein cifs-utils, kein Laufwerk im Dateisystem – also auch
nichts, in das man hineinlöschen kann. Pfade sind immer relativ zum Unterordner und nur mit „/“.
Fehler werden auf wenige Codes abgebildet, die die Admin-Konsole erklärt.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK = 4 << 20
TIMEOUT_S = 15
NOT_FOUND = (0xC0000034, 0xC000003A)          # Datei bzw. Pfad nicht vorhanden
SHARE_MISSING = (0xC00000CC, 0xC0000225)      # Freigabe unbekannt (Samba antwortet je nach Version anders)
DENIED = (0xC0000022,)


class RemoteError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _code(e: BaseException) -> str:
    """SMB-Fehler → Code. Reihenfolge wichtig: SMBOSError erbt von OSError, darf aber nie „unreachable“ sein."""
    import smbprotocol.exceptions as ex
    if isinstance(e, (ex.LogonFailure, ex.SMBAuthenticationError)):
        return "auth_failed"
    if isinstance(e, ex.BadNetworkName):
        return "share_not_found"
    status = getattr(e, "ntstatus", None)
    if isinstance(e, ex.AccessDenied) or status in DENIED:
        return "not_writable"
    if status in NOT_FOUND:
        return "not_found"
    if status in SHARE_MISSING:
        return "share_not_found"
    if isinstance(e, (ex.SMBOSError, ex.SMBResponseException, ex.SMBException)):
        return "unexpected"
    if isinstance(e, (ValueError, OSError, ConnectionError, TimeoutError)):
        return "unreachable"
    return "unexpected"


class SmbRemote:
    def __init__(self, cfg: dict) -> None:
        self.host, self.share = cfg["host"], cfg["share"]
        self.subdir = cfg.get("subdir") or ""
        self.base = rf"\\{self.host}\{self.share}"
        self._user, self._pw = cfg.get("user") or None, cfg.get("password") or None

    def _unc(self, rel: str = "") -> str:
        parts = [p for p in f"{self.subdir}/{rel}".split("/") if p]
        if any(p == ".." for p in parts):
            raise RemoteError("invalid_path")
        return "\\".join([self.base, *parts])

    def _call(self, fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except RemoteError:
            raise
        except Exception as e:  # noqa: BLE001 – alles Fremde wird zu einem erklärbaren Code
            code = _code(e)
            logger.info("Archiv-Server %s: %s (%s)", self.host, code, type(e).__name__)
            raise RemoteError(code) from e

    def login(self) -> None:
        import smbclient
        self._call(smbclient.register_session, self.host, username=self._user, password=self._pw,
                   connection_timeout=TIMEOUT_S)
        self._call(smbclient.stat_volume, self.base)

    def _mkdirs(self, rel_dir: str) -> None:
        import smbclient
        self._call(smbclient.makedirs, self._unc(rel_dir), exist_ok=True)

    def put(self, rel: str, local: Path) -> None:
        """Erst .part schreiben, dann auf den Endnamen. Eine alte Datei wird vorher entfernt."""
        import smbclient
        self._mkdirs(rel.rsplit("/", 1)[0] if "/" in rel else "")
        dst, part = self._unc(rel), self._unc(rel + ".part")

        def upload() -> None:
            with open(local, "rb") as src, smbclient.open_file(part, mode="wb") as out:
                while chunk := src.read(CHUNK):
                    out.write(chunk)

        self._call(upload)
        if self.size(rel) is not None:
            self._call(smbclient.remove, dst)            # Samba erlaubt replace über bestehende Dateien nicht immer
        self._call(smbclient.rename, part, dst)

    def read_chunks(self, rel: str):
        import smbclient
        fh = self._call(smbclient.open_file, self._unc(rel), mode="rb")
        try:
            while chunk := self._call(fh.read, CHUNK):
                yield chunk
        finally:
            fh.close()

    def size(self, rel: str) -> int | None:
        import smbclient
        try:
            return self._call(smbclient.stat, self._unc(rel)).st_size
        except RemoteError as e:
            if e.code == "not_found":
                return None                               # Datei (noch) nicht da
            raise

    def free_bytes(self) -> int:
        import smbclient
        return int(self._call(smbclient.stat_volume, self._unc()).caller_available_size)

    def probe(self) -> None:
        import smbclient
        self.login()
        self._mkdirs("")
        probe = self._unc(".hydrahive-probe")

        def roundtrip() -> None:
            with smbclient.open_file(probe, mode="wb") as fh:
                fh.write(b"hydrahive")
            with smbclient.open_file(probe, mode="rb") as fh:
                if fh.read() != b"hydrahive":
                    raise RemoteError("not_writable")
            smbclient.remove(probe)

        self._call(roundtrip)


def connect(cfg: dict) -> SmbRemote:
    remote = SmbRemote(cfg)
    remote.login()
    return remote
