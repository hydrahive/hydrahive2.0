from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel

from hydrahive.agents import bootstrap as agent_bootstrap, config as agent_config
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.users import (
    create,
    delete,
    list_users,
    update_password,
    update_role,
)

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    new_password: str


class UpdateUserRequest(BaseModel):
    role: str | None = None


@router.get("", dependencies=[Depends(require_admin)])
def get_users() -> list[dict]:
    return list_users()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_user(req: CreateUserRequest) -> dict:
    try:
        create(req.username, req.password, req.role)
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "username_exists")
    agent_bootstrap.ensure_master(req.username)
    return {"username": req.username, "role": req.role}


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_user(username: str) -> None:
    for agent in agent_config.list_by_owner(username):
        agent_config.delete(agent["id"])
    delete(username)


@router.patch("/{username}", dependencies=[Depends(require_admin)])
def update_user(username: str, req: UpdateUserRequest) -> dict:
    if req.role is not None:
        try:
            update_role(username, req.role)
        except ValueError as e:
            msg = str(e)
            if msg == "last_admin":
                raise coded(status.HTTP_400_BAD_REQUEST, "last_admin_cannot_demote")
            if msg.startswith("Ungültige Rolle"):
                raise coded(status.HTTP_400_BAD_REQUEST, "invalid_role", role=req.role)
            raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}


@router.patch("/me/password")
def change_own_password(
    req: ChangePasswordRequest,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    try:
        update_password(username, req.new_password)
    except ValueError:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}


@router.patch("/{username}/password", dependencies=[Depends(require_admin)])
def change_password(username: str, req: ChangePasswordRequest) -> dict:
    try:
        update_password(username, req.new_password)
    except ValueError:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {"ok": True}
