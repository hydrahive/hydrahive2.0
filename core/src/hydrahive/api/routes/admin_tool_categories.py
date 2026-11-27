"""Admin-Route für Kategorie-Bestätigungen des Tool-Katalogs (Spec S2, K12): Liste, Bestätigen, Widerruf.

Die Identität kommt aus dem Token (``require_admin``), nie aus dem Body; ein ``approved_by`` im Body wird ignoriert.
Jede Änderung steht im Audit-Log (``catalog.categories``).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.catalog import categories

router = APIRouter(prefix="/api/admin/tool-categories", tags=["tool-categories"])
Admin = Annotated[tuple[str, str], Depends(require_admin)]


class ApproveBody(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    tool: str = Field(min_length=1, max_length=120)


@router.get("")
def list_categories(_: Admin) -> dict:
    return {"approvals": categories.list_approvals(),
            "categories": [{"name": n, "label": categories.CATEGORY_LABELS.get(n, ""),
                            "tools": list(categories.tools_in_category(n))} for n in sorted(categories.CATEGORY_MAP)]}


@router.post("")
def approve(body: ApproveBody, auth: Admin) -> dict:
    admin, _ = auth
    try:
        categories.approve(body.category, body.tool, admin)
    except PermissionError as exc:
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only", message=str(exc))
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, "validation_error", message=str(exc))
    return {"category": body.category, "tool": body.tool, "approved_by": admin}


@router.delete("/{category}/{tool}")
def revoke(category: str, tool: str, auth: Admin) -> dict:
    admin, _ = auth
    try:
        removed = categories.revoke(category, tool, admin)
    except PermissionError as exc:
        raise coded(status.HTTP_403_FORBIDDEN, "admin_only", message=str(exc))
    if not removed:
        raise coded(status.HTTP_404_NOT_FOUND, "tool_category_approval_not_found")
    return {"revoked": True}
