"""FHIR-Patientenakte — Import und Abfrage."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import fhir as fhir_db
from hydrahive.fhir_ega import convert_ega_zip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fhir", tags=["fhir"])


@router.post("/import")
async def import_bundle(
    bundle: dict,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """FHIR Bundle importieren (Upsert-Semantik)."""
    username, _ = auth
    try:
        result = fhir_db.upsert_bundle(bundle, user_id=username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_fhir_bundle", "message": str(exc)})
    logger.info("fhir_import user=%s imported=%d updated=%d errors=%d",
                username, result["imported"], result["updated"], result["errors"])
    return result


@router.post("/import-ega")
async def import_ega_zip(
    file: UploadFile,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """TK eGA Export-ZIP direkt importieren (wird intern zu FHIR konvertiert)."""
    username, _ = auth
    data = await file.read()
    try:
        bundle = convert_ega_zip(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_ega_zip", "message": str(exc)})
    try:
        result = fhir_db.upsert_bundle(bundle, user_id=username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_fhir_bundle", "message": str(exc)})
    logger.info("fhir_import_ega user=%s imported=%d updated=%d errors=%d",
                username, result["imported"], result["updated"], result["errors"])
    return result


@router.get("/resources/{resource_type}")
async def get_resources(
    resource_type: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Alle Ressourcen eines Typs für den eingeloggten User."""
    username, _ = auth
    resources = fhir_db.query_by_type(user_id=username, resource_type=resource_type)
    return {"resource_type": resource_type, "count": len(resources), "resources": resources}


@router.get("/summary")
async def get_summary(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Zähler pro Ressourcentyp."""
    username, _ = auth
    return fhir_db.summary(user_id=username)


@router.get("/timeline")
async def get_timeline(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Alle Ressourcen chronologisch."""
    username, _ = auth
    entries = fhir_db.timeline(user_id=username)
    return {"count": len(entries), "entries": entries}
