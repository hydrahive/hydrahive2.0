"""FastAPI-Dependency für Funktions-Freigaben (docs/specs/access-groups.md §9).

    router = APIRouter(dependencies=[Depends(require_capability("core.vms"))])

Baut auf require_principal auf: aktuelle Rolle, stabile user_id, API-Keys wie
ihr Nutzer. Nicht deklarierte Funktionen sind offen (siehe check.level).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, status

from hydrahive.access import check
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded


def require_capability(capability: str, level: str = "use") -> Callable[..., AuthPrincipal]:
    def _dep(principal: Annotated[AuthPrincipal, Depends(require_principal)]) -> AuthPrincipal:
        have = check.level(user_id=principal.user_id, role=principal.role, capability=capability)
        if have is None or (level == "manage" and have != "manage"):
            raise coded(status.HTTP_403_FORBIDDEN, "capability_denied", capability=capability)
        return principal

    _dep.__name__ = f"require_capability[{capability}]"
    return _dep
