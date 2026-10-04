"""Server-Kopplung HydraHive ↔ HydraHive — Admin-API (docs/specs/server-peering.md).

Etappe 1: eigener Kopplungscode, Partner per Code anlegen, Fingerprint
bestätigen, sperren, entfernen, freigegebene Agenten pflegen. Aufträge
zwischen den Servern folgen in Etappe 2.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.db import federation_peers as peers_db
from hydrahive.federation import peer_identity as ident

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federation/peers", tags=["federation"])

_Admin = Annotated[tuple[str, str], Depends(require_admin)]


class OwnCodeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    url: str = Field(min_length=8, max_length=256, pattern=r"^https://")


class PeerCreate(BaseModel):
    code: str = Field(min_length=10, max_length=4096)


class PeerConfirm(BaseModel):
    fingerprint: str = Field(min_length=1, max_length=64)


class PeerAgents(BaseModel):
    agent_ids: list[str] = Field(default_factory=list, max_length=200)


def _public(peer: dict) -> dict:
    out = {k: v for k, v in peer.items() if k != "public_key"}
    out["allowed_agents"] = peers_db.allowed_agents(peer["id"])
    return out


def _peer_or_404(peer_id: str) -> dict:
    peer = peers_db.get_peer(peer_id)
    if not peer:
        raise coded(status.HTTP_404_NOT_FOUND, "peer_not_found")
    return peer


def _norm_fp(fp: str) -> str:
    return "".join(fp.split()).lower()


@router.get("/identity")
def own_identity(_: _Admin) -> dict:
    pub = ident.public_key_b64()
    return {"fingerprint": ident.fingerprint(pub)}


@router.post("/identity/code")
def own_code(body: OwnCodeRequest, _: _Admin) -> dict:
    pub = ident.public_key_b64()
    return {
        "code": ident.pairing_code(body.name, body.url),
        "fingerprint": ident.fingerprint(pub),
    }


@router.get("")
def list_peers(_: _Admin) -> list[dict]:
    return [_public(p) for p in peers_db.list_peers()]


@router.post("", status_code=status.HTTP_201_CREATED)
def add_peer(body: PeerCreate, _: _Admin) -> dict:
    try:
        info = ident.parse_pairing_code(body.code)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "peer_code_invalid")
    if not info["url"].startswith("https://"):
        raise coded(status.HTTP_400_BAD_REQUEST, "peer_code_invalid")
    if info["public_key"] == ident.public_key_b64():
        raise coded(status.HTTP_400_BAD_REQUEST, "peer_is_self")
    if peers_db.get_by_public_key(info["public_key"]) or peers_db.get_by_name(info["name"]):
        raise coded(status.HTTP_409_CONFLICT, "peer_exists")
    try:
        peer = peers_db.create_peer(
            info["name"], info["url"], info["public_key"], ident.fingerprint(info["public_key"]),
        )
    except sqlite3.IntegrityError:
        raise coded(status.HTTP_409_CONFLICT, "peer_exists")
    logger.info("Server-Kopplung: Partner '%s' angelegt, wartet auf Bestätigung", peer["name"])
    return _public(peer)


@router.post("/{peer_id}/confirm")
def confirm_peer(peer_id: str, body: PeerConfirm, _: _Admin) -> dict:
    """Aktiviert erst, wenn der Admin den Fingerprint der Gegenseite abgetippt hat."""
    peer = _peer_or_404(peer_id)
    if _norm_fp(body.fingerprint) != _norm_fp(peer["fingerprint"]):
        raise coded(status.HTTP_400_BAD_REQUEST, "peer_fingerprint_mismatch")
    updated = peers_db.set_status(peer_id, "active")
    logger.info("Server-Kopplung: Partner '%s' bestätigt", peer["name"])
    return _public(updated)  # type: ignore[arg-type]


@router.post("/{peer_id}/block")
def block_peer(peer_id: str, _: _Admin) -> dict:
    peer = _peer_or_404(peer_id)
    updated = peers_db.set_status(peer_id, "blocked")
    logger.warning("Server-Kopplung: Partner '%s' gesperrt", peer["name"])
    return _public(updated)  # type: ignore[arg-type]


@router.delete("/{peer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_peer(peer_id: str, _: _Admin) -> None:
    peer = _peer_or_404(peer_id)
    peers_db.delete_peer(peer_id)
    logger.info("Server-Kopplung: Partner '%s' entfernt", peer["name"])


@router.put("/{peer_id}/agents")
def set_agents(peer_id: str, body: PeerAgents, _: _Admin) -> dict:
    """Freigaben (Spec: Rechte-Modell 2). Nur existierende lokale Agenten."""
    from hydrahive.agents import config as agent_config

    _peer_or_404(peer_id)
    unknown = [a for a in body.agent_ids if not agent_config.get(a)]
    if unknown:
        raise coded(status.HTTP_400_BAD_REQUEST, "peer_agent_unknown", agent_id=unknown[0])
    peers_db.set_allowed_agents(peer_id, body.agent_ids)
    return _public(_peer_or_404(peer_id))
