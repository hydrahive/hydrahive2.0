"""Admin-only, read-only Harness Doctor."""
from fastapi import APIRouter, Depends, Query

from hydrahive.api.middleware.auth import require_admin
from hydrahive.harness_doctor import run_doctor

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/harness-doctor", dependencies=[Depends(require_admin)])
def harness_doctor(hours: int = Query(168, ge=1, le=720)) -> dict:
    return run_doctor(hours)
