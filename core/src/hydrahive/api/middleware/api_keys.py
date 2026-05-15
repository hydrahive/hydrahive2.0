"""API-Key-Verwaltung — persistente Tokens ohne Ablaufdatum.

Neues Format (seit Migration #118): hhk_<key_id_16hex>_<random_43>
  verify() extrahiert die key_id, lädt genau diesen Eintrag → O(1), ein bcrypt-Call.

Altes Format (Fallback): hhk_<44 Base64url>
  Lineare Schleife mit key_prefix-Filter — bleibt bis alle alten Keys rotiert sind.
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
# Länge der eingebetteten Key-ID im neuen Format (token_hex(8) = 16 Hex-Zeichen)
_KEY_ID_HEX_LEN = 16
_PREFIX_LEN = 12  # nur für Altformat-Fallback


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


def _is_new_format(plain: str) -> bool:
    """Erkennt neues Format: hhk_<16 Hex-Zeichen>_<Rest>.
    Hex-Zeichen sind [0-9a-f] — kein Überschneidung mit Base64url-Uppercase."""
    rest = plain[len(PREFIX):]
    return (
        len(rest) > _KEY_ID_HEX_LEN + 1
        and rest[_KEY_ID_HEX_LEN] == "_"
        and all(c in "0123456789abcdef" for c in rest[:_KEY_ID_HEX_LEN])
    )


def create(name: str, username: str, role: str) -> str:
    """Erzeugt einen neuen API-Key im neuen Format. Gibt den Klartext zurück (einmalig)."""
    key_id = secrets.token_hex(8)            # 16 Hex-Zeichen
    random_part = secrets.token_urlsafe(32)  # 43 Zeichen
    plain = f"{PREFIX}{key_id}_{random_part}"
    key_hash = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
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
    data = _load()

    if _is_new_format(plain):
        # O(1): Key-ID direkt aus dem Plain-Key lesen, genau einen bcrypt-Call
        key_id = plain[len(PREFIX):len(PREFIX) + _KEY_ID_HEX_LEN]
        entry = data.get(key_id)
        if not entry:
            return None
        try:
            if bcrypt.checkpw(encoded, entry["key_hash"].encode()):
                return {"username": entry["username"], "role": entry["role"]}
        except Exception:
            pass
        return None

    # Altformat-Fallback: lineare Schleife mit key_prefix-Filter
    prefix = plain[:_PREFIX_LEN]
    for entry in data.values():
        if entry.get("key_prefix") != prefix:
            continue
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
