"""REST-API der Patientenakte. Token/JWT-Auth via require_auth.

Routing-Reihenfolge: literale Sichten (timeline/summary) stehen VOR der
generischen /{entity}-Route, sonst würde {entity} sie abfangen.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from hydrahive.api.middleware.auth import require_auth
from hydrahive.patientenakte import entities, patients, views
from hydrahive.patientenakte.schema import ENTITIES

router = APIRouter(prefix="/api/health/patientenakte", tags=["patientenakte"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _entity_or_404(entity: str) -> None:
    if entity not in ENTITIES:
        raise HTTPException(404, f"Unbekannte Entität: {entity}")


def _own_or_404(user_id: str, pid: str) -> None:
    if patients.get(user_id, pid) is None:
        raise HTTPException(404, "Patient nicht gefunden")


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
