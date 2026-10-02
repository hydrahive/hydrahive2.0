from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """A currently existing user resolved through an immutable ID."""

    user_id: str
    username: str
    role: str


def create_token(username: str, role: str, user_id: str | None = None) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if user_id:
        payload["uid"] = user_id
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise coded(status.HTTP_401_UNAUTHORIZED, "token_expired")
    except jwt.InvalidTokenError:
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")


def require_auth(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> tuple[str, str]:
    """Returns (username, AKTUELLE role). Raises 401 if not authenticated.

    Rolle und Existenz kommen aus users.json, nicht aus dem Token
    (middleware/_resolve.py, Task a9706460). Service-Keys liefern ihre
    Sonderrolle (z. B. projektx) und sind damit nie Admin.
    """
    if not creds:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    from hydrahive.api.middleware._resolve import resolve_credential

    ident = resolve_credential(creds.credentials)
    return ident.username, ident.role


def require_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthPrincipal:
    """Aktueller Nutzer mit fester ID. Service-Keys (ohne Nutzer) → 401.

    Gleiche Prüfung wie require_auth (middleware/_resolve.py), liefert aber
    zusätzlich die unveränderliche user_id. Neue benutzereigene Ressourcen
    sollten hierauf aufbauen.
    """
    if not creds:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    from hydrahive.api.middleware._resolve import resolve_credential

    ident = resolve_credential(creds.credentials)
    if ident.is_service:
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    return AuthPrincipal(user_id=ident.user_id, username=ident.username, role=ident.role)


def require_principal_or_query(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token: Annotated[str | None, Query()] = None,
) -> AuthPrincipal:
    """Wie require_principal, nimmt ohne Header aber auch ``?token=``.

    Für Modul-Routen: <audio>, <video>, <img> und EventSource können keinen
    Authorization-Header setzen (Task 95137212). Der Header hat Vorrang.
    """
    if creds:
        return require_principal(creds)
    if not token:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    return require_principal(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


def require_session_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthPrincipal:
    """Wie require_principal, aber nur mit Login-Sitzung (JWT), nicht mit API-Key.

    Für Aktionen, mit denen man sich dauerhaften Zugang verschaffen kann
    (API-Keys anlegen/löschen). Sonst könnte ein abgegriffener Key, auch über
    ein Agent-Credential-Profil, sich selbst Ersatz-Keys erzeugen (Task 9e9439ff).
    """
    from hydrahive.api.middleware._resolve import API_KEY_PREFIX

    if creds and creds.credentials.startswith(API_KEY_PREFIX):
        raise coded(status.HTTP_403_FORBIDDEN, "session_required")
    return require_principal(creds)


def require_admin(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> tuple[str, str]:
    """Returns (username, role). Raises 403 if not admin."""
    username, role = auth
    if role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    return username, role


def require_admin_principal(
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> AuthPrincipal:
    """Require a currently existing principal whose current role is admin."""
    if principal.role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    return principal


def get_current_user_optional(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> tuple[str, str] | None:
    """Returns (username, aktuelle role) or None if not authenticated. No 401 exception."""
    if not creds:
        return None
    from fastapi import HTTPException

    from hydrahive.api.middleware._resolve import resolve_credential
    try:
        ident = resolve_credential(creds.credentials)
    except HTTPException as e:
        logger.debug("optional auth: abgelehnt: %s", e.detail)
        return None
    return ident.username, ident.role
