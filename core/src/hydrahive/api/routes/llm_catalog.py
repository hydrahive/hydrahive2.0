"""LLM-Modell-Catalog-API: Live-Listing + Test + Use-in-Agent."""
from __future__ import annotations

import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.llm import benchmark, capability_probe, catalog as catalog_mod, node_context, ollama_manager
from hydrahive.llm._config import load_config
from hydrahive.llm.ollama_common import normalize_model_name

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


class ProbeRequest(BaseModel):
    model: str


@router.post("/probes", status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(require_admin)])
async def start_capability_probe(req: ProbeRequest) -> dict:
    """Start a safe native tool-call probe for an Ollama model."""
    if not req.model.startswith("ollama/"):
        raise coded(status.HTTP_400_BAD_REQUEST, "probe_model_invalid")
    try:
        model = f"ollama/{normalize_model_name(req.model)}"
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "probe_model_invalid") from None
    provider = ollama_manager.configured_provider()
    if not provider:
        raise coded(status.HTTP_409_CONFLICT, "ollama_not_configured")
    node = node_context.for_provider(provider)
    return await capability_probe.start_probe(model, node_id=node["node_id"])


@router.get("/probes/{job_id}", dependencies=[Depends(require_admin)])
def get_capability_probe(job_id: str) -> dict:
    job = capability_probe.get_probe(job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "capability_probe_not_found")
    return job


@router.post("/benchmarks", status_code=status.HTTP_202_ACCEPTED,
             dependencies=[Depends(require_admin)])
async def start_benchmark(req: ProbeRequest) -> dict:
    """Start a short throughput benchmark and return a pollable job."""
    if not req.model.startswith("ollama/"):
        raise coded(status.HTTP_400_BAD_REQUEST, "benchmark_model_invalid")
    try:
        model = f"ollama/{normalize_model_name(req.model)}"
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "benchmark_model_invalid") from None
    provider = ollama_manager.configured_provider()
    if not provider:
        raise coded(status.HTTP_409_CONFLICT, "ollama_not_configured")
    node = node_context.for_provider(provider)
    return await benchmark.start_benchmark(model, node_id=node["node_id"])


@router.get("/benchmarks/{job_id}", dependencies=[Depends(require_admin)])
def get_benchmark(job_id: str) -> dict:
    job = benchmark.get_benchmark(job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "benchmark_not_found")
    return job


class UseInAgentRequest(BaseModel):
    agent_id: str
    model: str


def _ensure_model_in_providers(model: str) -> None:
    """Trägt das Modell in den passenden Provider von llm.json ein wenn nicht da.

    Provider-Zuordnung über das Prefix (nvidia_nim/, openai/, gemini/, …) bzw.
    bekannte Patterns (claude-* → anthropic, MiniMax-/abab → minimax).
    """
    from hydrahive.settings import settings
    if not settings.llm_config.exists():
        return
    data = json.loads(settings.llm_config.read_text())
    providers = data.get("providers", [])

    pid = None
    if model.startswith("nvidia_nim/"):
        pid = "nvidia"
    elif model.startswith("openai/"):
        pid = "openai"
    elif model.startswith("groq/"):
        pid = "groq"
    elif model.startswith("mistral/"):
        pid = "mistral"
    elif model.startswith("gemini/"):
        pid = "gemini"
    elif model.startswith("openrouter/"):
        pid = "openrouter"
    elif model.startswith("ollama/"):
        pid = "ollama"
    elif model.startswith("claude-"):
        pid = "anthropic"
    elif model.startswith("MiniMax") or model.startswith("abab") or model.startswith("embo-"):
        pid = "minimax"
    if not pid:
        return  # unbekannt → validate_model wird's eh durchwinken weil "available" leer ist

    p = next((x for x in providers if x.get("id") == pid), None)
    if not p:
        return  # Provider gar nicht konfiguriert — der Agent-Call wird sowieso scheitern, lieber dort
    if model in p.get("models", []):
        return
    p.setdefault("models", []).append(model)
    settings.llm_config.write_text(json.dumps(data, indent=2))


@router.post("/use-in-agent", dependencies=[Depends(require_admin)])
async def use_in_agent(req: UseInAgentRequest) -> dict:
    """Setzt agent.llm_model auf das gewählte Modell.

    Trägt das Modell automatisch in die Provider-Modellliste ein wenn nicht
    drin (sonst würde agent-validate_model rumblocken).
    """
    from hydrahive.agents import config as agent_config
    from hydrahive.agents._validation import AgentValidationError
    agent = agent_config.get(req.agent_id)
    if not agent:
        raise coded(status.HTTP_404_NOT_FOUND, "agent_not_found")
    _ensure_model_in_providers(req.model)
    try:
        agent_config.update(req.agent_id, llm_model=req.model)
    except AgentValidationError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "agent_invalid", message=str(e))
    return {"ok": True, "agent_id": req.agent_id, "llm_model": req.model}
