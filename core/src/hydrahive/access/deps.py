"""FastAPI-Dependency für Funktions-Freigaben (docs/specs/access-groups.md §9).

    router = APIRouter(dependencies=[Depends(require_capability("core.vms"))])

Baut auf require_principal auf: aktuelle Rolle, stabile user_id, API-Keys wie
ihr Nutzer. Nicht deklarierte Funktionen sind offen (siehe check.level).
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, status

from hydrahive.access import check
from hydrahive.api.middleware.auth import (
    AuthPrincipal,
    require_principal,
    require_principal_or_query,
)
from hydrahive.api.middleware.errors import coded


def require_capability(
    capability: str, level: str = "use", *, allow_query_token: bool = False,
) -> Callable[..., AuthPrincipal]:
    """allow_query_token: auch ``?token=`` statt Header (nur Modul-Tor, Task 95137212)."""
    principal_dep = require_principal_or_query if allow_query_token else require_principal

    # Depends als Default statt in Annotated: wegen ``from __future__ import
    # annotations`` sucht FastAPI Annotationen nur in den Modul-Globals — eine
    # lokale Variable dort würde als Query-Parameter missverstanden (422).
    def _dep(principal: AuthPrincipal = Depends(principal_dep)) -> AuthPrincipal:
        have = check.level(user_id=principal.user_id, role=principal.role, capability=capability)
        if have is None or (level == "manage" and have != "manage"):
            raise coded(status.HTTP_403_FORBIDDEN, "capability_denied", capability=capability)
        return principal

    _dep.__name__ = f"require_capability[{capability}]"
    return _dep
