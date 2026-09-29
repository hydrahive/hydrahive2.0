"""GET /api/access/me — eigene Freigaben (docs/specs/access-groups.md §9, §10).

Das Frontend nutzt die Antwort für Menü-Filter, Seiten-Sperre und „Meine Freigaben“.
``declared`` sind alle geprüften Funktionen. Was nicht darin steht, ist offen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.access import check, store
from hydrahive.access.capabilities import CATALOG
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
        "declared": [c.id for c in CATALOG.all()],
        "groups": groups,
    }
