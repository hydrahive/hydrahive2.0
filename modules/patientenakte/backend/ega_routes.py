"""TK eGA — nativer Import und Abfrage."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from hydrahive.api.middleware.auth import require_auth
from . import ega_store as ega_db
from .fhir_ega import extract_ega_records

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ega", tags=["ega"])


@router.post("/import")
async def import_ega(
    file: UploadFile,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """TK eGA Export-ZIP importieren (nativ, ohne FHIR-Konvertierung)."""
    username, _ = auth
    data = await file.read()
    try:
        records = extract_ega_records(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_ega_zip", "message": str(exc)})
    result = ega_db.upsert_records(records, user_id=username)
    logger.info("ega_import user=%s imported=%d updated=%d errors=%d",
                username, result["imported"], result["updated"], result["errors"])
    return result


@router.get("/summary")
async def get_summary(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    return ega_db.summary(user_id=username)


@router.get("/records/{dto_type}")
async def get_records(
    dto_type: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    records = ega_db.query_by_type(user_id=username, dto_type=dto_type)
    return {"dto_type": dto_type, "count": len(records), "records": records}


@router.get("/costs")
async def get_costs(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    return ega_db.cost_summary(user_id=username)


@router.get("/timeline")
async def get_timeline(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    entries = ega_db.timeline(user_id=username)
    return {"count": len(entries), "entries": entries}
