"""Butler-Editor: Beschreibung der Bausteine aus Modulen (docs/specs/butler-module-nodes.md §3).

Liefert nur Modul-Bausteine – die eingebauten kennt die Oberfläche fest. Nur Beschreibungen (Label, Text,
ParamSchema), keine Daten; deshalb für jeden angemeldeten Nutzer.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

router = APIRouter(prefix="/api/butler", tags=["butler"])


def module_nodes() -> list[dict]:
    from hydrahive.butler.registry import ACTIONS, CONDITIONS, TRIGGERS
    from hydrahive.modules.butler_bridge import MODULE_SUBTYPES

    registries = {"trigger": TRIGGERS, "condition": CONDITIONS, "action": ACTIONS}
    out: list[dict] = []
    for (node_type, subtype), module in sorted(MODULE_SUBTYPES.items()):
        spec = registries[node_type].get(subtype)
        if spec is None:
            continue
        out.append({"type": node_type, "subtype": subtype, "module": module, "label": spec.label,
                    "description": spec.description, "params": [asdict(p) for p in spec.params],
                    "implemented": getattr(spec, "implemented", True)})
    return out


@router.get("/registry")
def registry(_auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    return {"nodes": module_nodes()}
