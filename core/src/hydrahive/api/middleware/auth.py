from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

_bearer = HTTPBearer(auto_error=False)


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
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
    except Exception:
        return None
