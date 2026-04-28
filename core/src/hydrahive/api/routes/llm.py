from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.llm import client as llm_client
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


class TestRequest(BaseModel):
    model: str | None = None


@router.post("/test", dependencies=[Depends(require_admin)])
async def test_connection(req: TestRequest) -> dict:
    try:
        result = await llm_client.complete(
            messages=[{"role": "user", "content": "Reply with exactly one word: OK"}],
            model=req.model or None,
            max_tokens=10,
        )
        return {"ok": True, "response": result.strip()}
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
