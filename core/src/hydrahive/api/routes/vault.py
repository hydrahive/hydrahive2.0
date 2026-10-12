"""Vault-Schnittstellen (docs/specs/vault.md §4.2–4.4).

Alle Routen nur mit **Login-Sitzung**, nicht mit API-Key: Wer per Skript zugreift, braucht keine PIN, darf sie
aber auch nicht setzen oder benutzen. PIN festlegen und zurücksetzen nur mit dem Login-Passwort.
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin, require_session_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.vault import lockout, pins, tokens

router = APIRouter(prefix="/api/vault", tags=["vault"])
Session = Annotated[AuthPrincipal, Depends(require_session_principal)]


class PinIn(BaseModel):
    pin: str = Field(max_length=64)


class PasswordPinIn(PinIn):
    password: str = Field(max_length=512)


def _check_password(p: AuthPrincipal, password: str) -> None:
    if not users.verify(p.username, password):
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")


def _set(p: AuthPrincipal, pin: str) -> dict:
    try:
        gen = pins.set_pin(p.user_id, pin)
    except pins.PinFormatError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "vault_pin_format", message=str(e)) from e
    lockout.reset(p.user_id)
    return {"vault_token": tokens.issue(p.user_id, generation=gen, now=time.time())}


@router.get("/status")
def vault_status(p: Session, x_hh_vault: Annotated[str | None, Header(alias="X-HH-Vault")] = None) -> dict:
    is_set = pins.is_set(p.user_id)
    left = tokens.remaining(x_hh_vault, p.user_id, generation=pins.generation(p.user_id), now=time.time()) if is_set else 0
    return {"pin_set": is_set, "unlocked": left > 0, "remaining_seconds": left, "idle_seconds": tokens.IDLE_SECONDS}


@router.post("/setup")
def setup(body: PasswordPinIn, p: Session) -> dict:
    """Erste PIN: nur mit Login-Passwort (ein gestohlenes Token reicht nicht)."""
    _check_password(p, body.password)
    if pins.is_set(p.user_id):
        raise coded(status.HTTP_409_CONFLICT, "vault_pin_exists")
    return _set(p, body.pin)


@router.post("/unlock")
def unlock(body: PinIn, p: Session) -> dict:
    locked, retry = lockout.is_locked(p.user_id)
    if locked:
        exc = coded(status.HTTP_429_TOO_MANY_REQUESTS, "vault_too_many_attempts", retry_after=retry)
        exc.headers = {"Retry-After": str(retry)}
        raise exc
    if not pins.verify(p.user_id, body.pin):
        lockout.record_failure(p.user_id)
        raise coded(status.HTTP_401_UNAUTHORIZED, "vault_pin_wrong", pin_set=pins.is_set(p.user_id))
    lockout.reset(p.user_id)
    return {"vault_token": tokens.issue(p.user_id, generation=pins.generation(p.user_id), now=time.time())}


@router.post("/lock")
def lock(p: Session) -> dict:
    """Sofort sperren: alle Vault-Tokens dieses Nutzers werden ungültig (generation +1, PIN bleibt)."""
    if pins.is_set(p.user_id):
        pins.bump(p.user_id)
    return {"ok": True}


@router.post("/reset")
def reset_own(body: PasswordPinIn, p: Session) -> dict:
    """PIN vergessen: mit Login-Passwort eine neue PIN setzen. Alte Entsperrungen werden ungültig."""
    _check_password(p, body.password)
    return _set(p, body.pin)


@router.post("/admin/reset/{user_id}", dependencies=[Depends(require_admin)])
def reset_by_admin(user_id: str) -> dict:
    """Admin entfernt die PIN. Er erfährt sie nie und kann keine setzen; der Nutzer vergibt beim nächsten Öffnen
    selbst eine neue (mit seinem Login-Passwort)."""
    if not users.get_by_id(user_id):
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    pins.reset(user_id)
    lockout.reset(user_id)
    return {"ok": True}
