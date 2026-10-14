"""Einstellungen des externen Servers fürs Archiv (Spec archiv-system.md, Etappe 3).

Gehört dem System, nicht einem Nutzer: config_dir/archive-remote.json, Passwort mit
credentials/_crypto verschlüsselt. Nach außen (`public`) nie das Passwort, nur ob eines gesetzt ist.
Aktiv schalten geht nur, wenn genau diese Daten erfolgreich getestet wurden (`fingerprint`).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.smbmounts.models import HOST_RE, SHARE_RE

logger = logging.getLogger(__name__)

NAME = "archive-remote.json"
_HOST, _SHARE = re.compile(HOST_RE), re.compile(SHARE_RE)
_SUBDIR = re.compile(r"^[A-Za-z0-9._ -]+(/[A-Za-z0-9._ -]+)*$")
_USER = re.compile(r"^[A-Za-z0-9._@\\-]{0,128}$")
FIELDS = ("host", "share", "subdir", "user")


class RemoteConfigError(ValueError):
    def __init__(self, code: str, field: str | None = None) -> None:
        super().__init__(code)
        self.code, self.field = code, field


def _path() -> Path:
    return Path(settings.config_dir) / NAME


def _read() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        logger.warning("Archiv-Server-Einstellung unlesbar – gilt als nicht eingetragen")
        return {}


def _write(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _clean(values: dict) -> dict:
    host = str(values.get("host") or "").strip()
    share = str(values.get("share") or "").strip()
    subdir = str(values.get("subdir") or "").strip().strip("/").replace("\\", "/")
    user = str(values.get("user") or "").strip()
    if not _HOST.match(host):
        raise RemoteConfigError("archive_remote_invalid", "host")
    if not _SHARE.match(share) or "\\" in share or "/" in share:
        raise RemoteConfigError("archive_remote_invalid", "share")
    if subdir and (not _SUBDIR.match(subdir) or ".." in subdir.split("/")):
        raise RemoteConfigError("archive_remote_invalid", "subdir")
    if not _USER.match(user):
        raise RemoteConfigError("archive_remote_invalid", "user")
    return {"host": host, "share": share, "subdir": subdir, "user": user}


def save(values: dict) -> dict:
    """Speichert. Leeres Passwort behält das alte. Geänderte Daten → nicht mehr getestet, nicht aktiv."""
    from hydrahive.credentials._crypto import encrypt
    old = _read()
    new = _clean(values)
    pw = str(values.get("password") or "")
    new["password"] = encrypt(pw, settings.data_dir) if pw else old.get("password", "")
    fp_old = fingerprint(old)
    new["tested_fp"] = old.get("tested_fp") if fingerprint(new) == fp_old else None
    new["active"] = bool(old.get("active")) and new["tested_fp"] is not None
    _write(new)
    return public()


def load() -> dict | None:
    """Mit entschlüsseltem Passwort – nur für remote_smb.connect. None = nicht eingetragen."""
    from hydrahive.credentials._crypto import decrypt
    data = _read()
    if not data.get("host"):
        return None
    out = {k: data.get(k, "") for k in FIELDS}
    out["password"] = decrypt(data["password"], settings.data_dir) if data.get("password") else ""
    return out


def fingerprint(data: dict | None = None) -> str | None:
    """Was zusammen getestet wurde. Ändert sich eins davon, muss neu getestet werden."""
    data = _read() if data is None else data
    if not data.get("host"):
        return None
    raw = "\0".join(str(data.get(k, "")) for k in (*FIELDS, "password"))
    return hashlib.sha256(raw.encode()).hexdigest()


def mark_tested(fp: str | None) -> None:
    data = _read()
    if fp and fp == fingerprint(data):
        data["tested_fp"] = fp
        _write(data)


def set_active(active: bool) -> dict:
    data = _read()
    if active and (not data.get("tested_fp") or data["tested_fp"] != fingerprint(data)):
        raise RemoteConfigError("archive_remote_untested")
    data["active"] = bool(active)
    _write(data)
    return public()


def is_active() -> bool:
    data = _read()
    return bool(data.get("active")) and data.get("tested_fp") == fingerprint(data)


def public() -> dict:
    data = _read()
    out = {k: data.get(k, "") for k in FIELDS}
    fp = fingerprint(data)
    out.update(configured=bool(data.get("host")), password_set=bool(data.get("password")),
               tested=bool(fp) and data.get("tested_fp") == fp, active=is_active())
    return out


def test() -> dict:
    """Anmelden, Unterordner anlegen, Probedatei schreiben/lesen/löschen. Merkt sich den Erfolg."""
    from hydrahive.archive import remote_smb
    cfg = load()
    if cfg is None:
        return {"ok": False, "error": "not_configured"}
    fp = fingerprint()
    try:
        remote = remote_smb.connect(cfg)
        remote.probe()
        free = remote.free_bytes()
    except remote_smb.RemoteError as e:
        return {"ok": False, "error": e.code}
    mark_tested(fp)
    return {"ok": True, "free_bytes": free}


def reset_for_tests() -> None:
    _path().unlink(missing_ok=True)
