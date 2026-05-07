"""Zahnfee — Config, Briefing-Abruf und manueller Trigger."""
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.zahnfee import config as cfg_mod
from hydrahive.zahnfee import storage

router = APIRouter(prefix="/api/zahnfee", tags=["zahnfee"])

Auth = Annotated[tuple[str, str], Depends(require_auth)]
Admin = Annotated[tuple[str, str], Depends(require_admin)]


@router.get("/briefing")
def get_briefing(_: Auth) -> dict:
    briefing = storage.load()
    if not briefing:
        return {"briefing": None}
    return {"briefing": asdict(briefing)}


@router.get("/config")
def get_config(_: Admin) -> dict:
    return asdict(cfg_mod.load())


class ConfigBody(BaseModel):
    enabled: bool | None = None
    model: str | None = Field(default=None, max_length=200)
    run_hour: int | None = Field(default=None, ge=0, le=23)
    lookback_hours: int | None = Field(default=None, ge=1, le=168)
    source_datamining: bool | None = None
    source_mail: bool | None = None
    soul: str | None = Field(default=None, max_length=8000)


@router.put("/config")
def update_config(body: ConfigBody, _: Admin) -> dict:
    cfg = cfg_mod.load()
    for field_name, value in body.model_dump(exclude_none=True).items():
        setattr(cfg, field_name, value)
    cfg_mod.save(cfg)
    return asdict(cfg)


@router.post("/run")
async def manual_run(_: Admin) -> dict:
    """Zahnfee manuell triggern — für Tests und manuelle Briefings."""
    import asyncio
    from hydrahive.zahnfee import runner
    asyncio.create_task(runner.run(), name="zahnfee-manual")
    return {"ok": True, "message": "Zahnfee läuft — Briefing in Kürze verfügbar"}
