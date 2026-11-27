"""Messung des Tool-Katalogs je Sitzung (Spec V7/K8): ``GET /api/catalog/metrics?session_id=``.

Nur der Besitzer der Sitzung oder ein Admin. Die Identität kommt aus dem Token. Fremde und unbekannte Sitzungen liefern
dieselbe Antwort (404), damit niemand per Probieren erfährt, welche Sitzungs-IDs es gibt.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.catalog import metrics
from hydrahive.db import sessions as sessions_db

router = APIRouter(tags=["catalog"])


@router.get("/api/catalog/metrics")
def get_metrics(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    session_id: Annotated[str, Query(min_length=1, max_length=64)],
) -> dict:
    username, role = auth
    session = sessions_db.get(session_id)
    if not session or (role != "admin" and session.user_id != username):
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    return metrics.summary(session_id)
