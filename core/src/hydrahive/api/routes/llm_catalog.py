"""LLM-Modell-Catalog-API: Live-Listing + Test + Use-in-Agent."""
from __future__ import annotations

import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.llm import catalog as catalog_mod
from hydrahive.llm._config import load_config

router = APIRouter(prefix="/api/llm/catalog", tags=["llm-catalog"])


@router.get("", dependencies=[Depends(require_admin)])
async def get_catalog() -> dict:
    """Catalog für alle in llm.json konfigurierten Provider."""
    cfg = load_config()
    providers = cfg.get("providers", [])
    entries = await catalog_mod.catalog_for_providers(providers)
    return {"providers": entries}


class TestRequest(BaseModel):
    model: str


@router.post("/test", dependencies=[Depends(require_admin)])
async def test_model(req: TestRequest) -> dict:
    """1-Mini-Call → {ok, latency_ms, response, error?}."""
    from hydrahive.llm import client as llm_client
    t0 = time.time()
    try:
        out = await llm_client.complete(
            messages=[{"role": "user", "content": "Reply with exactly one word: OK"}],
            model=req.model,
            max_tokens=10,
        )
        return {
            "ok": True,
            "latency_ms": int((time.time() - t0) * 1000),
            "response": out.strip()[:200],
        }
    except Exception as e:
        return {
            "ok": False,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": str(e)[:400],
        }


class UseInAgentRequest(BaseModel):
    agent_id: str
    model: str


@router.post("/use-in-agent", dependencies=[Depends(require_admin)])
async def use_in_agent(req: UseInAgentRequest) -> dict:
    """Setzt agent.llm_model auf das gewählte Modell."""
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(req.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    agent_config.update(req.agent_id, llm_model=req.model)
    return {"ok": True, "agent_id": req.agent_id, "llm_model": req.model}
