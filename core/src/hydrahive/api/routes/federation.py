"""Federation API — Workstation-Registry + A2A-Card-Refresh + Client-Config-Generator."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware import api_keys as ak
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.db import federation as fed_db
from hydrahive.federation.registry import fetch_card

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federation", tags=["federation"])

_auth = require_auth
_admin = require_admin


class WorkstationCreate(BaseModel):
    name: str
    url: str
    token: str = ""
    enabled: bool = True
    # Default True (safe). Flip to False ONLY for self-signed LAN/
    # Tailnet peers — the registry's httpx client honours it.
    verify_tls: bool = True


class WorkstationUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    token: str | None = None
    enabled: bool | None = None
    verify_tls: bool | None = None


def _strip_token(ws: dict) -> dict:
    """Token nicht ans Frontend schicken — nur ob gesetzt."""
    out = {k: v for k, v in ws.items() if k not in ("token", "card_json")}
    out["has_token"] = bool(ws.get("token"))
    # Ensure verify_tls is always present in the API response (bool).
    out["verify_tls"] = bool(ws.get("verify_tls", 1))
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
        name=body.name,
        url=body.url,
        token=body.token,
        enabled=body.enabled,
        verify_tls=body.verify_tls,
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
    ws = fed_db.get_workstation(ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workstation nicht gefunden")
    if not ws.get("token"):
        raise HTTPException(status_code=400, detail="Kein Token konfiguriert")
    url = f"{ws['url']}/remote/audit"
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            verify=bool(ws.get("verify_tls", 1)),
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {ws['token']}",
                    "X-Caller": "hydrahive2",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Client-Config-Generator ──────────────────────────────────────────────────
# Erzeugt Import-Configs für ProjektX-Clients: API-Key + Tailscale-Authkey +
# AgentLink-Koordinaten in einer einzigen JSON-Datei.

class ClientCreate(BaseModel):
    name: str


@router.get("/clients")
def list_clients(
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> list[dict]:
    return [k for k in ak.list_keys() if k.get("role") == "projektx"]


@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> dict:
    from hydrahive.settings import settings
    from hydrahive.tailscale.status import get_status
    from hydrahive.tailscale.admin import create_invite

    plain_key = ak.create(name=body.name, username="admin", role="projektx")
    # Key-ID ist in den ersten 16 Hex-Zeichen nach "hhk_" kodiert
    key_id = plain_key[len(ak.PREFIX): len(ak.PREFIX) + ak._KEY_ID_HEX_LEN]

    ts = await get_status()
    tailscale_section: dict | None = None
    if ts.get("connected"):
        authkey: str | None = None
        try:
            invite = await create_invite()
            authkey = invite.get("auth_key") or None
        except Exception as exc:
            # Invite ist optional (Tailscale evtl. ohne Auth-Key-Rechte) — der
            # Rest der Antwort bleibt gültig, aber der Grund soll auffindbar sein.
            logger.warning("Tailscale-Invite konnte nicht erstellt werden: %s", exc)
        tailscale_section = {
            "ip": ts.get("ip"),
            "hostname": ts.get("hostname"),
            "dns_name": ts.get("dns_name"),
            "authkey": authkey,
        }

    port = settings.port
    ts_ip = ts.get("ip")
    ts_dns = ts.get("dns_name")

    config: dict = {
        "schema": "hh2_client_v1",
        "name": body.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hh2": {
            "api_url": f"http://{ts_ip}:{port}" if ts_ip else None,
            "api_url_dns": f"https://{ts_dns}:{port}" if ts_dns else None,
            "api_key": plain_key,
        },
        "agentlink": {
            "url": settings.agentlink_url or None,
            "ws_url": settings.agentlink_ws_url or None,
            "agent_id": settings.agentlink_agent_id,
        } if settings.agentlink_url else None,
        "tailscale": tailscale_section,
    }

    return {"key_id": key_id, "name": body.name, "config": config}


@router.delete("/clients/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    key_id: str,
    _: Annotated[tuple[str, str], Depends(_admin)],
) -> None:
    if not ak.delete(key_id):
        raise HTTPException(status_code=404, detail="Client nicht gefunden")
