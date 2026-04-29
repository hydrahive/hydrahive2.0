from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from hydrahive.api.middleware import lockout
from hydrahive.api.middleware.auth import create_token, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import verify

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str
    role: str


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request) -> LoginResponse:
    ip = _client_ip(request)
    locked, retry_after = lockout.is_locked(req.username, ip)
    if locked:
        exc = coded(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_login_attempts", retry_after=retry_after)
        exc.headers = {"Retry-After": str(retry_after)}
        raise exc
    user = verify(req.username, req.password)
    if not user:
        lockout.record_failure(req.username, ip)
        raise coded(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")
    lockout.reset(req.username, ip)
    token = create_token(user["username"], user["role"])
    return LoginResponse(access_token=token, username=user["username"], role=user["role"])


@router.get("/me")
def me(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    username, role = auth
    return {"username": username, "role": role}
