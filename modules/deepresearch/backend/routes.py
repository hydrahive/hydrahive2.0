"""Deep-Research-Modul — FastAPI-Router (/api/modules/deepresearch/*)."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth

from . import service

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class RunIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model: str | None = None


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def start_run(body: RunIn, auth: Auth) -> dict[str, Any]:
    run_id = await service.start_run(auth[0], body.question.strip(), body.model)
    return {"run_id": run_id}


@router.get("/runs")
def list_runs(auth: Auth) -> list[dict[str, Any]]:
    return service.list_runs(auth[0])


@router.get("/runs/{run_id}")
def get_run(run_id: str, auth: Auth) -> dict[str, Any]:
    run = service.get_run(auth[0], run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lauf nicht gefunden")
    return run
