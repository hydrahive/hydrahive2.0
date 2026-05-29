"""Admin-CRUD für die Forschungs-API-Registry.

GET liefert die Quellen ohne Klartext-Key (nur has_key). PATCH setzt enabled/key.
POST .../test macht einen Reachability-Check auf die base_url. Alle Endpoints
admin-only — wie die LLM-Seite (geteilte Recherche-Infra).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hydrahive import research
from hydrahive.api.middleware.auth import require_admin

router = APIRouter(prefix="/api/research-apis", tags=["research-apis"])


class ApiUpdate(BaseModel):
    enabled: bool | None = None
    key: str | None = None


@router.get("")
async def list_apis(_=Depends(require_admin)):
    return {"apis": research.list_public()}


@router.patch("/{rid}")
async def update_api(rid: str, body: ApiUpdate, _=Depends(require_admin)):
    if research.get_api(rid) is None:
        raise HTTPException(status_code=404, detail="unknown research api")
    if body.enabled is not None:
        research.set_enabled(rid, body.enabled)
    if body.key is not None:
        research.set_key(rid, body.key)
    return research.get_api(rid).public_dict()


@router.post("/{rid}/test")
async def test_api(rid: str, _=Depends(require_admin)):
    """Health-Check: GET auf die base_url (bestätigt Erreichbarkeit/Config)."""
    a = research.get_api(rid)
    if a is None:
        raise HTTPException(status_code=404, detail="unknown research api")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(a.base_url)
        return {"ok": r.status_code < 500, "status": r.status_code}
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e)}
