"""GUI-editierbare Settings (Admin) — Schema + Werte lesen/schreiben.

Schreibt Overrides in `config_dir/overrides.json` (Auflösung Override → Env →
Default, siehe `settings.overrides`). Secrets werden maskiert ausgeliefert.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import overrides, settings
from hydrahive.settings.editable import BY_KEY, EDITABLE_SETTINGS

router = APIRouter(prefix="/api/system", tags=["system"])


def _serialize(key: str) -> dict:
    s = BY_KEY[key]
    over = overrides.get_overrides()
    value = overrides.resolve(key)
    return {
        "key": s.key,
        "group": s.group,
        "label": s.label,
        "type": s.type,
        "help": s.help,
        "value": "" if s.type == "secret" else value,   # Secret nie roh ausliefern
        "is_set": bool(value),                            # ob (irgendwo) ein Wert existiert
        "overridden": s.key in over,                      # per GUI gesetzt (vs Env/Default)
    }


@router.get("/settings", dependencies=[Depends(require_admin)])
def get_settings() -> dict:
    return {"settings": [_serialize(s.key) for s in EDITABLE_SETTINGS]}


@router.get("/mail-defaults", dependencies=[Depends(require_admin)])
def get_mail_defaults() -> dict:
    """Effektive globale Mail-Config als Platzhalter fürs per-Buddy-Postfach.
    IMAP-Host/-Login aus SMTP abgeleitet (settings.mail_imap_*). Ohne Passwort.
    Admin-only wie der Rest von /api/system/* — die globale Infra-Config ist nicht
    für Nicht-Admins. Nicht-Admin-UI bekommt 403 → einfach keine Platzhalter."""
    return {
        "smtp": {
            "host": settings.mail_smtp_host,
            "port": settings.mail_smtp_port,
            "user": settings.mail_smtp_user,
            "from": settings.mail_from,
        },
        "imap": {
            "host": settings.mail_imap_host,
            "port": settings.mail_imap_port,
            "user": settings.mail_imap_user,
        },
    }


class SettingUpdate(BaseModel):
    value: str = ""


@router.put("/settings/{key}", dependencies=[Depends(require_admin)])
def update_setting(key: str, body: SettingUpdate) -> dict:
    s = BY_KEY.get(key)
    if s is None:
        raise coded(status.HTTP_404_NOT_FOUND, "setting_not_found")

    value = body.value
    if s.type == "secret" and value == "":
        # leeres Secret = „nicht ändern" (GET liefert Secrets eh maskiert)
        return _serialize(key)
    if value == "":
        overrides.clear_override(key)  # zurück auf Env/Default
    else:
        overrides.set_override(key, value)
    return _serialize(key)
