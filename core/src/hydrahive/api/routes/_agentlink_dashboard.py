"""Login für das AgentLink-Dashboard (Task 3bd963b2, b2).

AgentLink hat keine Anmeldung, nginx gibt es unter /agentlink/ frei. Das
HydraHive-Login liegt im Browser in sessionStorage und wird bei einer
Navigation nicht mitgeschickt. Deshalb:

- ``POST dashboard-session`` (nur Admins) stellt ein eigenes, kurzlebiges
  Cookie aus: HttpOnly, Secure, SameSite=Strict, nur für /agentlink/.
  Inhalt: user_id und Ablauf, signiert mit einem zweckgebundenen Schlüssel.
  Es ist kein Login-Token und öffnet keine HydraHive-API.
- ``GET dashboard-auth`` prüft das Cookie für nginx (auth_request): Signatur,
  Ablauf und ob der Nutzer NOCH existiert und Admin ist. 204 oder 401.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.settings import settings

router = APIRouter(prefix="/api/agentlink", tags=["agentlink"])

COOKIE = "hh_agentlink"
PATH = "/agentlink/"
MAX_AGE = 8 * 3600
_CONTEXT = b"hydrahive-agentlink-dashboard-v1"
_MAX_LEN = 512


def _key() -> bytes:
    return hmac.new(settings.secret_key.encode(), _CONTEXT, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _issue(user_id: str) -> str:
    body = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + MAX_AGE}).encode())
    sig = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def _admin_from(cookie: str | None) -> bool:
    if not cookie or len(cookie) > _MAX_LEN or cookie.count(".") != 1:
        return False
    body, sig = cookie.split(".")
    expected = _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        data = json.loads(_unb64(body))
        uid, exp = data["uid"], int(data["exp"])
    except (ValueError, KeyError, TypeError):
        return False
    if exp < time.time() or not isinstance(uid, str):
        return False
    from hydrahive.api.middleware.users import get_by_id

    current = get_by_id(uid)
    return bool(current and current["role"] == "admin")


@router.post("/dashboard-session")
def dashboard_session(
    response: Response,
    admin: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    response.set_cookie(
        COOKIE, _issue(admin.user_id), max_age=MAX_AGE, path=PATH,
        httponly=True, secure=True, samesite="strict",
    )
    return {"url": settings.agentlink_dashboard_url or PATH}


@router.get("/dashboard-auth", status_code=status.HTTP_204_NO_CONTENT)
def dashboard_auth(hh_agentlink: Annotated[str | None, Cookie()] = None) -> Response:
    if not _admin_from(hh_agentlink):
        raise coded(status.HTTP_401_UNAUTHORIZED, "agentlink_dashboard_login_required")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
