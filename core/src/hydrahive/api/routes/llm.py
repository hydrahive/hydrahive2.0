from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.settings import settings

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LlmProvider(BaseModel):
    id: str
    name: str
    api_key: str
    models: list[str]


class LlmConfig(BaseModel):
    providers: list[LlmProvider] = []
    default_model: str = ""


def _load() -> dict:
    if not settings.llm_config.exists():
        return {"providers": [], "default_model": ""}
    return json.loads(settings.llm_config.read_text())


def _save(data: dict) -> None:
    settings.llm_config.parent.mkdir(parents=True, exist_ok=True)
    settings.llm_config.write_text(json.dumps(data, indent=2))


@router.get("", dependencies=[Depends(require_admin)])
def get_config() -> dict:
    return _load()


@router.put("", dependencies=[Depends(require_admin)])
def update_config(cfg: LlmConfig) -> dict:
    data = cfg.model_dump()
    _save(data)
    return data
