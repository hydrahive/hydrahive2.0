from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, status
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
    """Returns (username, role). Raises 401 if not authenticated."""
    if not creds:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    token = creds.credentials
    if token.startswith("hhk_"):
        from hydrahive.api.middleware.api_keys import verify as verify_key
        user = verify_key(token)
        if not user:
            raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")
        return user["username"], user["role"]
    payload = _decode(token)
    return payload["sub"], payload["role"]


def require_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthPrincipal:
    """Resolve an authenticated credential against the current user store.

    Unlike ``require_auth``, this rejects legacy credentials without an immutable
    user ID as well as credentials for deleted/recreated or renamed users. New
    user-owned resources should depend on this function.
    """
    if not creds:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")

    token = creds.credentials
    credential: dict
    if token.startswith("hhk_"):
        from hydrahive.api.middleware.api_keys import verify as verify_key
        credential = verify_key(token) or {}
        user_id = credential.get("user_id")
    else:
        credential = _decode(token)
        user_id = credential.get("uid")

    if not isinstance(user_id, str) or not user_id:
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")

    from hydrahive.api.middleware.users import get_by_id
    current = get_by_id(user_id)
    if not current or current["username"] != credential.get("sub", credential.get("username")):
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")

    # API keys are explicit credential grants. A role change invalidates them;
    # JWTs instead receive the user's current role immediately.
    if token.startswith("hhk_") and current["role"] != credential.get("role"):
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_token")

    return AuthPrincipal(
        user_id=current["user_id"],
        username=current["username"],
        role=current["role"],
    )


def require_admin(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> tuple[str, str]:
    """Returns (username, role). Raises 403 if not admin."""
    username, role = auth
    if role != "admin":
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    return username, role


def get_current_user_optional(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> tuple[str, str] | None:
    """Returns (username, role) or None if not authenticated. No 401 exception."""
    if not creds:
        return None
    try:
        token = creds.credentials
        if token.startswith("hhk_"):
            from hydrahive.api.middleware.api_keys import verify as verify_key
            user = verify_key(token)
            if not user:
                return None
            return user["username"], user["role"]
        payload = _decode(token)
        return payload["sub"], payload["role"]
    except Exception as e:
        logger.debug("optional auth: token-decode fehlgeschlagen: %s", e)
        return None
