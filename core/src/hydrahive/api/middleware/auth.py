from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token abgelaufen")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ungültiger Token")


def require_auth(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> tuple[str, str]:
    """Returns (username, role). Raises 401 if not authenticated."""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht authentifiziert")
    payload = _decode(creds.credentials)
    return payload["sub"], payload["role"]


def require_admin(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> tuple[str, str]:
    """Returns (username, role). Raises 403 if not admin."""
    username, role = auth
    if role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nur für Admins")
    return username, role
