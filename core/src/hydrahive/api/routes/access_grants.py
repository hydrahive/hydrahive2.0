"""Admin-API: Katalog und Funktions-Freigaben (docs/specs/access-groups.md §10).

``GET /api/access/capabilities`` liefert alles, was die Freigabe-Tabelle braucht:
Funktionen mit ihren Freigaben, Gruppen und Nutzer.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from hydrahive.access import grants, store
from hydrahive.access.capabilities import catalog
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.users import get_by_id, list_users

router = APIRouter(prefix="/api/access", tags=["access"])
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]

SubjectType = Literal["user", "group", "everyone"]


class GrantKey(BaseModel):
    capability: str = Field(min_length=1, max_length=120)
    subject_type: SubjectType
    subject_id: str = Field(default="", max_length=128)


class GrantIn(GrantKey):
    level: Literal["use", "manage"]


def _check_target(key: GrantKey) -> None:
    if not catalog().is_declared(key.capability):
        raise coded(status.HTTP_400_BAD_REQUEST, "capability_unknown", capability=key.capability)
    if key.subject_type == "everyone" and key.subject_id:
        raise coded(status.HTTP_400_BAD_REQUEST, "subject_invalid")
    if key.subject_type != "everyone" and not key.subject_id:
        raise coded(status.HTTP_400_BAD_REQUEST, "subject_invalid")
    if key.subject_type == "user" and get_by_id(key.subject_id) is None:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    if key.subject_type == "group" and store.get_group(key.subject_id) is None:
        raise coded(status.HTTP_404_NOT_FOUND, "group_not_found")


@router.get("/capabilities")
def capabilities(_admin: Admin) -> dict:
    by_cap: dict[str, list[dict]] = {}
    for g in grants.all_grants():
        by_cap.setdefault(g["capability"], []).append(
            {"subject_type": g["subject_type"], "subject_id": g["subject_id"], "level": g["level"]})
    return {
        "capabilities": [
            {"id": c.id, "label": c.label, "default": c.default, "module_id": c.module_id,
             "tools": list(c.tools), "grants": by_cap.get(c.id, [])}
            for c in catalog().all()
        ],
        "groups": [{"id": g["id"], "name": g["name"]} for g in store.list_groups()],
        "users": [u for u in list_users() if u["role"] != "admin"],
    }


@router.put("/grants", status_code=status.HTTP_204_NO_CONTENT)
def put_grant(body: GrantIn, admin: Admin) -> None:
    _check_target(body)
    grants.grant(body.capability, body.subject_type, body.subject_id, body.level, actor_id=admin.user_id)


@router.delete("/grants", status_code=status.HTTP_204_NO_CONTENT)
def delete_grant(
    admin: Admin,
    capability: Annotated[str, Query(min_length=1, max_length=120)],
    subject_type: Annotated[SubjectType, Query()],
    subject_id: Annotated[str, Query(max_length=128)] = "",
) -> None:
    if (subject_type == "everyone") == bool(subject_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "subject_invalid")
    grants.revoke(capability, subject_type, subject_id, actor_id=admin.user_id)
