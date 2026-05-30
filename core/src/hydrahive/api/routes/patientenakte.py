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
from hydrahive.patientenakte import entities, patients, views
from hydrahive.patientenakte.schema import ENTITIES, ui_schema

router = APIRouter(prefix="/api/health/patientenakte", tags=["patientenakte"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _entity_or_404(entity: str) -> None:
    if entity not in ENTITIES:
        raise HTTPException(404, f"Unbekannte Entität: {entity}")


def _own_or_404(user_id: str, pid: str) -> None:
    if patients.get(user_id, pid) is None:
        raise HTTPException(404, "Patient nicht gefunden")


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


# ── Multi-Patient Routes (Admin/Explizit) ─────────────────────────────────────
# MUST come before /{entity} or FastAPI catches /patients as entity="patients"

@router.get("/patients")
async def list_patients(auth: Auth) -> list[dict[str, Any]]:
    return patients.list_for(auth[0])


@router.post("/patients")
async def create_patient(data: dict[str, Any], auth: Auth) -> dict[str, str]:
    return {"id": patients.create(auth[0], data)}


@router.get("/patients/{pid}")
async def get_patient(pid: str, auth: Auth) -> dict[str, Any]:
    p = patients.get(auth[0], pid)
    if p is None:
        raise HTTPException(404, "Patient nicht gefunden")
    p["counts"] = views.summary(auth[0], pid)
    return p


@router.patch("/patients/{pid}")
async def update_patient(pid: str, data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    _own_or_404(auth[0], pid)
    return {"ok": patients.update(auth[0], pid, data)}


@router.delete("/patients/{pid}")
async def delete_patient(pid: str, auth: Auth) -> dict[str, bool]:
    _own_or_404(auth[0], pid)
    return {"ok": patients.delete(auth[0], pid)}


@router.get("/patients/{pid}/timeline")
async def timeline(pid: str, auth: Auth) -> list[dict[str, Any]]:
    _own_or_404(auth[0], pid)
    return views.timeline(auth[0], pid)


@router.get("/patients/{pid}/summary")
async def summary(pid: str, auth: Auth) -> dict[str, int]:
    _own_or_404(auth[0], pid)
    return views.summary(auth[0], pid)


@router.get("/patients/{pid}/{entity}")
async def list_entity(pid: str, entity: str, auth: Auth,
                      q: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    return entities.list_for(auth[0], pid, entity, q=q, status=status)


@router.post("/patients/{pid}/{entity}")
async def create_entity(pid: str, entity: str, data: dict[str, Any], auth: Auth) -> dict[str, str]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    return {"id": entities.create(auth[0], pid, entity, data)}


@router.post("/patients/{pid}/{entity}/batch")
async def batch_entity(pid: str, entity: str, body: dict[str, Any], auth: Auth) -> dict[str, int]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    return {"created": entities.batch_create(auth[0], pid, entity, body.get("items", []))}


@router.get("/patients/{pid}/{entity}/{eid}")
async def get_entity(pid: str, entity: str, eid: str, auth: Auth) -> dict[str, Any]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    rec = entities.get(auth[0], pid, entity, eid)
    if rec is None:
        raise HTTPException(404, "Eintrag nicht gefunden")
    return rec


@router.patch("/patients/{pid}/{entity}/{eid}")
async def update_entity(pid: str, entity: str, eid: str, data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    return {"ok": entities.update(auth[0], pid, entity, eid, data)}


@router.delete("/patients/{pid}/{entity}/{eid}")
async def delete_entity(pid: str, entity: str, eid: str, auth: Auth) -> dict[str, bool]:
    _entity_or_404(entity)
    _own_or_404(auth[0], pid)
    return {"ok": entities.delete(auth[0], pid, entity, eid)}


# ── Single-User: Generic Entity CRUD ─────────────────────────────────────────
# These /{entity} routes come AFTER /patients/* routes

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