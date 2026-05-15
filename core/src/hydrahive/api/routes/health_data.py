"""Apple Health Auto Export — Ingest + Abfrage."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import health as health_db
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health-data", tags=["health"])


def _check_key(
    x_hh_health_key: str | None,
    authorization: str | None,
    query_key: str | None = None,
) -> None:
    expected = settings.health_api_key
    if not expected:
        raise HTTPException(status_code=403, detail="health_ingest_disabled")
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
    if x_hh_health_key != expected and bearer != expected and query_key != expected:
        raise HTTPException(status_code=401, detail="bad_key")


@router.post("/ingest")
async def ingest(
    payload: dict,
    x_hh_health_key: Annotated[str | None, Header(alias="X-HH-Health-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    key: str | None = Query(default=None),
    x_automation_name: Annotated[str | None, Header(alias="automation-name")] = None,
    x_automation_id: Annotated[str | None, Header(alias="automation-id")] = None,
    x_session_id: Annotated[str | None, Header(alias="session-id")] = None,
    x_period: Annotated[str | None, Header(alias="automation-period")] = None,
    x_aggregation: Annotated[str | None, Header(alias="automation-aggregation")] = None,
) -> dict:
    _check_key(x_hh_health_key, authorization, key)

    data = payload.get("data", payload)
    metrics = data.get("metrics", []) if isinstance(data, dict) else []
    workouts = data.get("workouts", []) if isinstance(data, dict) else []
    logger.info(
        "health_ingest: %s metrics, %s workouts von automation='%s'",
        len(metrics), len(workouts), x_automation_name,
    )

    record_id = health_db.insert(
        payload=payload,
        automation_name=x_automation_name,
        automation_id=x_automation_id,
        session_id=x_session_id,
        period=x_period,
        aggregation=x_aggregation,
    )
    return {"id": record_id, "metrics": len(metrics), "workouts": len(workouts)}


@router.get("/data", dependencies=[Depends(require_auth)])
def list_data(
    limit: int = Query(default=50, ge=1, le=500),
    automation_id: str | None = Query(default=None),
) -> dict:
    rows = health_db.list_recent(limit=limit, automation_id=automation_id)
    return {"records": rows, "count": len(rows)}


@router.get("/metrics", dependencies=[Depends(require_auth)])
def get_metrics(
    days: int = Query(default=7, ge=1, le=365),
    metric: str | None = Query(default=None),
) -> dict:
    return health_db.get_metrics_summary(days=days, metric=metric)


@router.get("/data/{record_id}", dependencies=[Depends(require_auth)])
def get_record(record_id: str) -> dict:
    payload = health_db.get_payload(record_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="not_found")
    return {"id": record_id, "payload": payload}
