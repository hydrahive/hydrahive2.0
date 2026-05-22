"""Federation API — Workstation-Registry + A2A-Card-Refresh."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.db import federation as fed_db
from hydrahive.federation.registry import fetch_card

router = APIRouter(prefix="/api/federation", tags=["federation"])

_auth = require_auth
_admin = require_admin


class WorkstationCreate(BaseModel):
    name: str
    url: str
    token: str = ""
    enabled: bool = True


class WorkstationUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    token: str | None = None
    enabled: bool | None = None


def _strip_token(ws: dict) -> dict:
    """Token nicht ans Frontend schicken — nur ob gesetzt."""
    out = {k: v for k, v in ws.items() if k not in ("token", "card_json")}
    out["has_token"] = bool(ws.get("token"))
    return out


@router.get("/workstations")
def list_workstations(
    _: Annotated[tuple[str, str], Depends(_auth)],
) -> list[dict]:
    return [_strip_token(ws) for ws in fed_db.list_workstations()]


@router.post("/workstations", status_code=status.HTTP_201_CREATED)
def create_workstation(
    body: WorkstationCreate,
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> dict:
    ws = fed_db.create_workstation(
        name=body.name, url=body.url, token=body.token, enabled=body.enabled
    )
    return _strip_token(ws)


@router.put("/workstations/{ws_id}")
def update_workstation(
    ws_id: str,
    body: WorkstationUpdate,
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> dict:
    existing = fed_db.get_workstation(ws_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Workstation nicht gefunden")
    updates = body.model_dump(exclude_none=True)
    ws = fed_db.update_workstation(ws_id, **updates)
    return _strip_token(ws)  # type: ignore[arg-type]


@router.delete("/workstations/{ws_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workstation(
    ws_id: str,
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> None:
    if not fed_db.delete_workstation(ws_id):
        raise HTTPException(status_code=404, detail="Workstation nicht gefunden")


@router.post("/workstations/{ws_id}/refresh")
async def refresh_card(
    ws_id: str,
    _: Annotated[tuple[str, str], Depends(_auth)],
) -> dict:
    ws = fed_db.get_workstation(ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation nicht gefunden")
    card = await fetch_card(ws_id, force=True)
    if card is None:
        raise HTTPException(
            status_code=502,
            detail=f"A2A-Card von '{ws['name']}' nicht erreichbar",
        )
    return card


@router.get("/workstations/{ws_id}/audit")
async def get_audit(
    ws_id: str,
    _: Annotated[tuple[str, str], Depends(_auth)],
) -> list[dict]:
    """Holt Remote-Audit-Log von der Workstation."""
    import httpx
    ws = fed_db.get_workstation(ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation nicht gefunden")
    if not ws.get("token"):
        raise HTTPException(status_code=400, detail="Kein Token konfiguriert")
    url = f"{ws['url']}/remote/audit"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {ws['token']}", "X-Caller": "hydrahive2"},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
