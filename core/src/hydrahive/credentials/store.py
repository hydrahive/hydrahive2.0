"""File-Storage für Credentials. Pro User eine JSON-Datei.

Atomic write via temp+rename. chmod 600 sofort beim ersten Anlegen.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from hydrahive.credentials.models import (
    ALL_TYPES, Credential, CredentialType, is_valid_name, matches_url,
)
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


def _file_for(username: str) -> Path:
    return settings.data_dir / "credentials" / f"{username}.json"


def _load_raw(username: str) -> dict:
    path = _file_for(username)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("Defekter Credentials-File: %s", path)
        return {}


def _save_raw(username: str, data: dict) -> None:
    path = _file_for(username)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _row_to_credential(name: str, row: dict) -> Credential:
    t = row.get("type", "bearer")
    if t not in ALL_TYPES:
        t = "bearer"
    return Credential(
        name=name,
        type=t,  # type: ignore[arg-type]
        value=row.get("value", ""),
        url_pattern=row.get("url_pattern", "*"),
        description=row.get("description", ""),
        header_name=row.get("header_name", ""),
        query_param=row.get("query_param", ""),
    )


def list_credentials(username: str) -> list[Credential]:
    raw = _load_raw(username)
    return [_row_to_credential(n, v) for n, v in sorted(raw.items())]


def get_credential(username: str, name: str) -> Credential | None:
    raw = _load_raw(username)
    if name not in raw:
        return None
    return _row_to_credential(name, raw[name])


def save_credential(username: str, cred: Credential) -> tuple[bool, str]:
    if not is_valid_name(cred.name):
        return False, "credential_name_invalid"
    if cred.type not in ALL_TYPES:
        return False, "credential_type_invalid"
    if cred.type == "header" and not cred.header_name:
        return False, "credential_header_name_required"
    if cred.type == "query" and not cred.query_param:
        return False, "credential_query_param_required"
    raw = _load_raw(username)
    raw[cred.name] = {
        "type": cred.type, "value": cred.value, "url_pattern": cred.url_pattern,
        "description": cred.description, "header_name": cred.header_name,
        "query_param": cred.query_param,
    }
    _save_raw(username, raw)
    return True, ""


def delete_credential(username: str, name: str) -> bool:
    raw = _load_raw(username)
    if name not in raw:
        return False
    del raw[name]
    _save_raw(username, raw)
    return True


def match_credential(username: str, url: str, *, prefer_name: str | None = None) -> Credential | None:
    """Findet die passendste Credential für eine URL.

    Wenn prefer_name gesetzt: dieser Profile-Name wird zurückgegeben (sofern existent
    und URL gegen Pattern matcht). Sonst: erstes Credential dessen url_pattern matcht.
    """
    raw = _load_raw(username)
    if prefer_name:
        if prefer_name in raw:
            cred = _row_to_credential(prefer_name, raw[prefer_name])
            if matches_url(cred.url_pattern, url):
                return cred
        return None
    for name, row in raw.items():
        cred = _row_to_credential(name, row)
        if matches_url(cred.url_pattern, url):
            return cred
    return None
