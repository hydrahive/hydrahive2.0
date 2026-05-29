"""Persistenz der Forschungs-API-Registry.

Gespeichert werden nur die Admin-**Overrides** pro id (key/enabled/auth_param/
polite_email) in `research_apis.json` — beim Laden über den Seed gemergt. So
erscheinen neue Seed-Quellen automatisch, Admin-Edits bleiben erhalten. Keys
werden AES-GCM-verschlüsselt (wie der Credential-Store).
"""
from __future__ import annotations

import json
import logging
import os

from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.research._seed import SEED
from hydrahive.research.models import ResearchApi
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_OVERRIDE_FIELDS = ("key", "enabled", "polite_email", "auth_param")


def _load_overrides() -> dict:
    path = settings.research_apis_config
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("Defekte research_apis.json: %s", path)
        return {}
    for ov in raw.values():
        if isinstance(ov, dict) and ov.get("key"):
            ov["key"] = decrypt(ov["key"], settings.data_dir)
    return raw


def _save_overrides(overrides: dict) -> None:
    path = settings.research_apis_config
    path.parent.mkdir(parents=True, exist_ok=True)
    enc = {
        rid: {**ov, "key": encrypt(ov["key"], settings.data_dir)} if ov.get("key") else ov
        for rid, ov in overrides.items()
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(enc, indent=2, ensure_ascii=False))
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def list_apis() -> list[ResearchApi]:
    overrides = _load_overrides()
    out: list[ResearchApi] = []
    for base in SEED:
        ov = overrides.get(base.id, {})
        merged = {**base.__dict__, **{k: ov[k] for k in _OVERRIDE_FIELDS if k in ov}}
        out.append(ResearchApi(**merged))
    return out


def get_api(rid: str) -> ResearchApi | None:
    return next((a for a in list_apis() if a.id == rid), None)


def list_public() -> list[dict]:
    return [a.public_dict() for a in list_apis()]


def _set_override(rid: str, **fields) -> bool:
    if not any(s.id == rid for s in SEED):
        return False
    overrides = _load_overrides()
    overrides.setdefault(rid, {}).update(fields)
    _save_overrides(overrides)
    return True


def set_key(rid: str, key: str) -> bool:
    return _set_override(rid, key=key)


def set_enabled(rid: str, enabled: bool) -> bool:
    return _set_override(rid, enabled=enabled)
