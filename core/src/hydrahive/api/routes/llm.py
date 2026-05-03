from __future__ import annotations

import json

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel

from typing import Annotated

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.llm import client as llm_client
from hydrahive.llm._minimax_usage import fetch_usage as fetch_minimax_usage
from hydrahive.llm import embed as llm_embed
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
    embed_model: str = ""


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
        raise coded(status.HTTP_400_BAD_REQUEST, "llm_test_failed", message=str(e))


@router.get("/embed-models", dependencies=[Depends(require_admin)])
def get_embed_models() -> list[dict]:
    """Gibt Embedding-Modelle zurück für die ein API-Key konfiguriert ist."""
    return llm_embed.available_for_config(_load())


@router.get("/minimax/usage")
async def minimax_usage(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """MiniMax token_plan/remains pro Modell. Auch für non-admin sichtbar — nur Quota-Info."""
    return await fetch_minimax_usage()
