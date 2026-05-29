"""Persistenz der Forschungs-API-Registry.

Gespeichert werden nur die Admin-**Overrides** pro id (key/enabled) in
`research_apis.json` — beim Laden über den Seed gemergt. So erscheinen neue
Seed-Quellen automatisch, Admin-Edits bleiben erhalten. Keys werden AES-GCM-
verschlüsselt (wie der Credential-Store).
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

_OVERRIDE_FIELDS = ("key", "enabled")


def _load_overrides() -> dict:
    path = settings.research_apis_config
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("Defekte research_apis.json: %s", path)
        return {}
    for rid, ov in raw.items():
        if isinstance(ov, dict) and ov.get("key"):
            try:
                ov["key"] = decrypt(ov["key"], settings.data_dir)
            except Exception as e:
                logger.warning(
                    "research_apis: Key für '%s' nicht entschlüsselbar (%s) — ignoriert", rid, e)
                ov.pop("key", None)
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


def match_research_api(url: str):
    """Erst-passende aktivierte Registry-API mit gesetztem Key → Credential-
    Äquivalent (oder None). Keyless/ohne Key → None (keine Injektion nötig).
    Gibt ein hydrahive.credentials.models.Credential zurück, damit fetch_url's
    _apply_auth es unverändert verarbeitet."""
    from hydrahive.credentials.models import Credential, matches_url
    for a in list_apis():
        if not (a.enabled and a.key and a.auth_type in ("query", "header", "bearer")):
            continue
        if not matches_url(a.url_pattern, url):
            continue
        return Credential(
            name=f"research:{a.id}", type=a.auth_type, value=a.key,
            url_pattern=a.url_pattern,
            header_name=a.auth_param if a.auth_type == "header" else "",
            query_param=a.auth_param if a.auth_type == "query" else "",
        )
    return None
