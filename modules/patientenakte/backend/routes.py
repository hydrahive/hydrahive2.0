"""REST-API der Patientenakte. Token/JWT-Auth via require_auth.

Routing-Reihenfolge: literale Sichten (timeline/summary) stehen VOR der
generischen /{entity}-Route, sonst würde {entity} sie abfangen.

WICHTIG: /patients/* Routen müssen VOR /{entity} kommen, da FastAPI in
Registrierungs-Reihenfolge matcht. Sonst fängt /{entity} = "patients" ab.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from hydrahive.api.middleware.auth import require_auth
from . import entities, patients, views
from .schema import ENTITIES, ui_schema

router = APIRouter(prefix="/akte", tags=["patientenakte"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _entity_or_404(entity: str) -> None:
    if entity not in ENTITIES:
        raise HTTPException(404, f"Unbekannte Entität: {entity}")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE ORDER MATTERS: FastAPI matches in definition order.
# 1. Literal root:  /  POST/GET/PATCH
# 2. Literal views:  /timeline  /summary
# 3. Multi-patient:  /patients/*  ← MUST be before /{entity} or it gets caught
# 4. Generic:        /{entity}/*
# ─────────────────────────────────────────────────────────────────────────────

# ── Single-User: Root ────────────────────────────────────────────────────────

@router.get("")
async def get_my_akte(auth: Auth) -> dict[str, Any]:
    """Hole die eigene Akte des eingeloggten Users. 404 wenn noch keine existiert."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden. Bitte zuerst anlegen.")
    p = patients.get(auth[0], pid)
    if p is None:
        raise HTTPException(404, "Keine Akte vorhanden. Bitte zuerst anlegen.")
    p["counts"] = views.summary(auth[0], pid)
    return p


@router.post("")
async def create_my_akte(data: dict[str, Any], auth: Auth) -> dict[str, str]:
    """Erstellt die eigene Akte. Scheitert wenn bereits eine existiert."""
    existing = patients.get_own_id(auth[0])
    if existing is not None:
        raise HTTPException(409, "Akte existiert bereits.")
    return {"id": patients.create(auth[0], data)}


@router.patch("")
async def update_my_akte(data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    """Aktualisiert die eigenen Akte-Stammdaten."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    return {"ok": patients.update(auth[0], pid, data)}


# ── Single-User: Literal Views ────────────────────────────────────────────────

@router.get("/_schema")
async def get_schema(auth: Auth) -> dict[str, Any]:
    """Die UI-Registry (SSOT) — Frontend rendert Formulare/Spalten generisch.

    Literale Route VOR /{entity}, sonst fängt der Catch-all "_schema" als
    unbekannte Entität ab. Keine Akte nötig — reine Metadaten.
    """
    return ui_schema()


@router.get("/timeline")
async def my_timeline(auth: Auth) -> list[dict[str, Any]]:
    """Chronologischer Zeitstrahl über alle Entity-Typen der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    return views.timeline(auth[0], pid)


@router.get("/summary")
async def my_summary(auth: Auth) -> dict[str, int]:
    """Count aller Entity-Typen der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    return views.summary(auth[0], pid)


# ── Single-User: Generic Entity CRUD ─────────────────────────────────────────
# "Jeder User eine Akte" — get_own_id() löst die eigene Akte auf. Eine
# Multi-Patient-/patients/*-Familie gab es mal (spekulative Mehrmandanten-
# fähigkeit), wurde aber nie verdrahtet und 2026-06 entfernt (#195).

@router.get("/{entity}")
async def list_my_entity(entity: str, auth: Auth,
                         q: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    """Liste Einträge einer Entity der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    return entities.list_for(auth[0], pid, entity, q=q, status=status)


@router.post("/{entity}")
async def create_my_entity(entity: str, data: dict[str, Any], auth: Auth) -> dict[str, str]:
    """Neuer Eintrag in einer Entity der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    return {"id": entities.create(auth[0], pid, entity, data)}


@router.post("/{entity}/batch")
async def batch_my_entity(entity: str, body: dict[str, Any], auth: Auth) -> dict[str, int]:
    """Batch-Import in eigene Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    return {"created": entities.batch_create(auth[0], pid, entity, body.get("items", []))}


@router.get("/{entity}/{eid}")
async def get_my_entity(entity: str, eid: str, auth: Auth) -> dict[str, Any]:
    """Einzelner Eintrag aus der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    rec = entities.get(auth[0], pid, entity, eid)
    if rec is None:
        raise HTTPException(404, "Eintrag nicht gefunden")
    return rec


@router.patch("/{entity}/{eid}")
async def update_my_entity(entity: str, eid: str, data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    """Aktualisiert einen Eintrag in der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    return {"ok": entities.update(auth[0], pid, entity, eid, data)}


@router.delete("/{entity}/{eid}")
async def delete_my_entity(entity: str, eid: str, auth: Auth) -> dict[str, bool]:
    """Löscht einen Eintrag aus der eigenen Akte."""
    pid = patients.get_own_id(auth[0])
    if pid is None:
        raise HTTPException(404, "Keine Akte vorhanden.")
    _entity_or_404(entity)
    return {"ok": entities.delete(auth[0], pid, entity, eid)}