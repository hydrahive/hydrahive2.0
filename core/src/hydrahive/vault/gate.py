"""Vault-Sperre als Dependency (docs/specs/vault.md §4.1, §4.3).

- Nur **Login-Token** (Oberfläche) brauchen die PIN. API-Keys (``hhk_…``) sind Hintergrund-Zugriff → frei.
- Vault-Token im Header ``X-HH-Vault`` oder als ``?vault=`` (für <audio>/<img>, die keinen Header setzen).
- Bei Erfolg kommt ein verlängerter Token im Antwort-Header ``X-HH-Vault-Refresh`` zurück (gleitende Sperre).
- Sonst ``423 vault_locked`` mit ``pin_set`` (False → Oberfläche zeigt „PIN festlegen“).
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, Header, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hydrahive.api.middleware._resolve import API_KEY_PREFIX
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal_or_query
from hydrahive.api.middleware.errors import coded
from hydrahive.vault import pins, tokens

_bearer = HTTPBearer(auto_error=False)


def _is_api_key(creds: HTTPAuthorizationCredentials | None, query_token: str | None) -> bool:
    raw = creds.credentials if creds else (query_token or "")
    return raw.startswith(API_KEY_PREFIX)


def require_vault_unlocked(
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(require_principal_or_query)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token: Annotated[str | None, Query()] = None,
    x_hh_vault: Annotated[str | None, Header(alias="X-HH-Vault")] = None,
    vault: Annotated[str | None, Query()] = None,
) -> AuthPrincipal:
    if _is_api_key(creds, token):
        return principal
    gen = pins.generation(principal.user_id)
    refreshed = tokens.refresh(x_hh_vault or vault, principal.user_id, generation=gen, now=time.time())
    if refreshed and pins.is_set(principal.user_id):
        response.headers["X-HH-Vault-Refresh"] = refreshed
        return principal
    raise coded(status.HTTP_423_LOCKED, "vault_locked", pin_set=pins.is_set(principal.user_id))
