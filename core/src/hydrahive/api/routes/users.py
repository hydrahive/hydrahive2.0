from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.agents import bootstrap as agent_bootstrap, config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.users import (
    create,
    delete,
    list_users,
    update_password,
)

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    new_password: str


@router.get("", dependencies=[Depends(require_admin)])
def get_users() -> list[dict]:
    return list_users()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(req: CreateUserRequest) -> dict:
    try:
        create(req.username, req.password, req.role)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    agent_bootstrap.ensure_master(req.username)
    return {"username": req.username, "role": req.role}


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_user(username: str) -> None:
    for agent in agent_config.list_by_owner(username):
        agent_config.delete(agent["id"])
    delete(username)


@router.patch("/me/password")
def change_own_password(
    req: ChangePasswordRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    try:
        update_password(username, req.new_password)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True}


@router.patch("/{username}/password", dependencies=[Depends(require_admin)])
def change_password(username: str, req: ChangePasswordRequest) -> dict:
    try:
        update_password(username, req.new_password)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True}
