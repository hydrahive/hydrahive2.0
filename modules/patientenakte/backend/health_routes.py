"""Apple Health Auto Export — Ingest + Abfrage."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.client_ip import client_ip
from hydrahive.api.middleware.inbound_ratelimit import check_rate
from hydrahive.api.middleware.secret_compare import verify_secret
from . import health_store as health_db
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health-data", tags=["health"])


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
    if not (verify_secret(x_hh_health_key, expected)
            or verify_secret(bearer, expected)
            or verify_secret(query_key, expected)):
        raise HTTPException(status_code=401, detail="bad_key")


@router.post("/ingest")
async def ingest(
    payload: dict,
    request: Request,
    x_hh_health_key: Annotated[str | None, Header(alias="X-HH-Health-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    key: str | None = Query(default=None),
    x_automation_name: Annotated[str | None, Header(alias="automation-name")] = None,
    x_automation_id: Annotated[str | None, Header(alias="automation-id")] = None,
    x_session_id: Annotated[str | None, Header(alias="session-id")] = None,
    x_period: Annotated[str | None, Header(alias="automation-period")] = None,
    x_aggregation: Annotated[str | None, Header(alias="automation-aggregation")] = None,
) -> dict:
    allowed, retry_after = check_rate(f"health-ingest:{client_ip(request)}")
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited",
                            headers={"Retry-After": str(retry_after)})
    _check_key(x_hh_health_key, authorization, key)

    if key is not None:
        # #207: Key im ?key=-Query landet in Access-/Proxy-Logs. Noch akzeptiert
        # (kein Bruch), aber der Pfad wird entfernt sobald der Client umgestellt ist.
        logger.warning(
            "health-ingest: Key via ?key=-Query empfangen — landet in Access-Logs. "
            "Client bitte auf Header 'X-HH-Health-Key' umstellen; der Query-Pfad "
            "wird danach entfernt (#207).",
        )

    # user_id kommt NICHT aus dem Request — der Key bindet an genau einen
    # konfigurierten User (Single-Device-Ingest). Verhindert Cross-User-PHI-Schreiben.
    user = settings.health_ingest_user

    data = payload.get("data", payload)
    metrics = data.get("metrics", []) if isinstance(data, dict) else []
    workouts = data.get("workouts", []) if isinstance(data, dict) else []
    logger.info(
        "health_ingest: user=%s, %s metrics, %s workouts von automation='%s'",
        user, len(metrics), len(workouts), x_automation_name,
    )

    record_id = health_db.insert(
        payload=payload,
        user_id=user,
        automation_name=x_automation_name,
        automation_id=x_automation_id,
        session_id=x_session_id,
        period=x_period,
        aggregation=x_aggregation,
    )
    return {"id": record_id, "metrics": len(metrics), "workouts": len(workouts)}


@router.get("/data")
def list_data(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    limit: int = Query(default=50, ge=1, le=500),
    automation_id: str | None = Query(default=None),
) -> dict:
    username, _ = auth
    rows = health_db.list_recent(user_id=username, limit=limit, automation_id=automation_id)
    return {"records": rows, "count": len(rows)}


@router.get("/metrics")
def get_metrics(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    days: int = Query(default=7, ge=1, le=365),
    metric: str | None = Query(default=None),
) -> dict:
    username, _ = auth
    return health_db.get_metrics_summary(user_id=username, days=days, metric=metric)


@router.get("/data/{record_id}")
def get_record(
    record_id: str,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    username, _ = auth
    payload = health_db.get_payload(record_id, user_id=username)
    if payload is None:
        raise HTTPException(status_code=404, detail="not_found")
    return {"id": record_id, "payload": payload}
