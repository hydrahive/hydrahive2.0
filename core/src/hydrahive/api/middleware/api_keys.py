"""API-Key-Verwaltung — persistente Tokens ohne Ablaufdatum.

Keys haben das Format hhk_<44 Base64url-Zeichen>.
Gespeichert wird nur der bcrypt-Hash. Der Klartext-Key wird nur einmalig
bei der Erzeugung zurückgegeben.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

import bcrypt

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

PREFIX = "hhk_"


def _path() -> Path:
    return settings.api_keys_config


def _load() -> dict:
    p = _path()
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


def create(name: str, username: str, role: str) -> str:
    """Erzeugt einen neuen API-Key. Gibt den Klartext-Key zurück (einmalig)."""
    plain = PREFIX + secrets.token_urlsafe(32)
    key_hash = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    key_id = secrets.token_hex(8)
    data = _load()
    data[key_id] = {
        "name": name,
        "key_hash": key_hash,
        "username": username,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)
    logger.info("API-Key '%s' für User '%s' angelegt", name, username)
    return plain


def verify(plain: str) -> dict | None:
    """Prüft einen API-Key. Gibt {username, role} zurück oder None."""
    if not plain.startswith(PREFIX):
        return None
    encoded = plain.encode()
    for entry in _load().values():
        try:
            if bcrypt.checkpw(encoded, entry["key_hash"].encode()):
                return {"username": entry["username"], "role": entry["role"]}
        except Exception:
            continue
    return None


def list_keys(username: str | None = None) -> list[dict]:
    """Listet alle Keys (ohne Hash). username=None → alle (admin)."""
    return [
        {"id": kid, "name": e["name"], "username": e["username"],
         "role": e["role"], "created_at": e["created_at"]}
        for kid, e in _load().items()
        if username is None or e["username"] == username
    ]


def delete(key_id: str, username: str | None = None) -> bool:
    """Löscht einen Key. username=None → admin darf alles löschen."""
    data = _load()
    entry = data.get(key_id)
    if not entry:
        return False
    if username is not None and entry["username"] != username:
        return False
    del data[key_id]
    _save(data)
    return True
