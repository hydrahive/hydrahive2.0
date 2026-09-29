"""GET /api/access/me — eigene Freigaben (docs/specs/access-groups.md §9, §10).

Das Frontend nutzt die Antwort für Menü-Filter, Seiten-Sperre und „Meine Freigaben“.
``declared`` sind alle geprüften Funktionen. Was nicht darin steht, ist offen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.access import check, store
from hydrahive.access.capabilities import catalog
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

router = APIRouter(prefix="/api/access", tags=["access"])


@router.get("/me")
def me(principal: Annotated[AuthPrincipal, Depends(require_principal)]) -> dict:
    groups = []
    for gid in store.groups_of(principal.user_id):
        g = store.get_group(gid)
        if g:
            groups.append({"id": g["id"], "name": g["name"]})
    return {
        "admin": principal.role == "admin",
        "capabilities": check.capabilities_for(user_id=principal.user_id, role=principal.role),
        "declared": [c.id for c in catalog().all()],
        "groups": groups,
    }


@router.get("/users/{username}")
def user_access(
    username: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    """Freigaben eines Nutzers für den Agent-Editor (gesperrte Werkzeuge anzeigen).

    Admins dürfen jeden Nutzer abfragen, andere nur sich selbst.
    """
    from fastapi import status

    from hydrahive.api.middleware.errors import coded
    from hydrahive.api.middleware.users import get_by_username
    if principal.role != "admin" and principal.username != username:
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only")
    user = get_by_username(username)
    if user is None:
        raise coded(status.HTTP_404_NOT_FOUND, "user_not_found")
    return {
        "admin": user["role"] == "admin",
        "capabilities": check.capabilities_for(user_id=user["user_id"], role=user["role"]),
        "declared": [c.id for c in catalog().all()],
    }
