"""Admin-API: Gruppen und Mitglieder (docs/specs/access-groups.md §10).

Nur Admins. Nutzer werden über die stabile user_id adressiert.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.access import store
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import get_by_id, list_users

router = APIRouter(prefix="/api/access/groups", tags=["access"])
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class GroupPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)


def _with_members(group: dict) -> dict:
    names = {u["user_id"]: u["username"] for u in list_users()}
    members = [{"user_id": uid, "username": names.get(uid, "")} for uid in store.members_of(group["id"])]
    return {**group, "members": members}


def _group_or_404(group_id: str) -> dict:
    group = store.get_group(group_id)
    if group is None:
        raise coded(status.HTTP_404_NOT_FOUND, "group_not_found")
    return group


@router.get("")
def list_groups(_admin: Admin) -> list[dict]:
    return store.list_groups()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group(body: GroupIn, admin: Admin) -> dict:
    try:
        group = store.create_group(body.name.strip(), body.description, actor_id=admin.user_id)
    except store.GroupExists:
        raise coded(status.HTTP_409_CONFLICT, "group_exists")
    return _with_members(group)


@router.get("/{group_id}")
def get_group(group_id: str, _admin: Admin) -> dict:
    return _with_members(_group_or_404(group_id))


@router.patch("/{group_id}")
def update_group(group_id: str, body: GroupPatch, admin: Admin) -> dict:
    try:
        group = store.update_group(
            group_id,
            name=body.name.strip() if body.name is not None else None,
            description=body.description,
            actor_id=admin.user_id,
        )
    except store.GroupNotFound:
        raise coded(status.HTTP_404_NOT_FOUND, "group_not_found")
    except store.GroupExists:
        raise coded(status.HTTP_409_CONFLICT, "group_exists")
    return _with_members(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, admin: Admin) -> None:
    try:
        store.delete_group(group_id, actor_id=admin.user_id)
    except store.GroupNotFound:
        raise coded(status.HTTP_404_NOT_FOUND, "group_not_found")


@router.put("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_member(group_id: str, user_id: str, admin: Admin) -> None:
    _group_or_404(group_id)
    if get_by_id(user_id) is None:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    store.add_member(group_id, user_id, actor_id=admin.user_id)


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(group_id: str, user_id: str, admin: Admin) -> None:
    _group_or_404(group_id)
    store.remove_member(group_id, user_id, actor_id=admin.user_id)
