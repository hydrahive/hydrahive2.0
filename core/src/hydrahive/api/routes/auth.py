from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import create_token, require_auth
from hydrahive.api.middleware.users import verify
from typing import Annotated
from fastapi import Depends

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    user = verify(req.username, req.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ungültige Zugangsdaten")
    token = create_token(user["username"], user["role"])
    return LoginResponse(access_token=token, username=user["username"], role=user["role"])


@router.get("/me")
def me(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    username, role = auth
    return {"username": username, "role": role}
