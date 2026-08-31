"""Admin-only Ollama model inventory and lifecycle endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded
from hydrahive.llm import ollama_client, ollama_lifecycle, ollama_manager
from hydrahive.llm.ollama_common import normalize_model_name, validate_family_name

router = APIRouter(
    prefix="/api/llm/catalog/ollama",
    tags=["llm-catalog"],
    dependencies=[Depends(require_admin)],
)


class PullRequest(BaseModel):
    model: str = Field(min_length=1, max_length=263)


def _provider() -> dict:
    provider = ollama_manager.configured_provider()
    if not provider:
        raise coded(status.HTTP_409_CONFLICT, "ollama_not_configured")
    return provider


@router.get("")
async def get_ollama_catalog() -> dict:
    return await ollama_manager.catalog_overview(ollama_manager.configured_provider())


@router.get("/library/{family}")
async def get_ollama_family(family: str) -> dict:
    try:
        name = validate_family_name(family)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_ollama_family") from None
    try:
        return await ollama_manager.family_variants(name, ollama_manager.configured_provider())
    except Exception:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "ollama_library_unavailable") from None


@router.post("/pulls", status_code=status.HTTP_202_ACCEPTED)
async def start_ollama_pull(request: PullRequest) -> dict:
    try:
        name = normalize_model_name(request.model)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_ollama_model") from None
    try:
        return await ollama_lifecycle.start_pull(_provider(), name)
    except ollama_client.OllamaUnavailable:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "ollama_unreachable") from None


@router.get("/pulls/{job_id}")
def get_ollama_pull(job_id: str) -> dict:
    job = ollama_lifecycle.get_pull(job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "ollama_pull_not_found")
    return job


@router.delete("/models/{model}")
async def delete_ollama_model(model: str) -> dict:
    try:
        name = normalize_model_name(model)
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_ollama_model") from None
    try:
        await ollama_lifecycle.delete_model(_provider(), name)
    except ollama_lifecycle.ModelInUse as exc:
        raise coded(status.HTTP_409_CONFLICT, "ollama_model_in_use", references=exc.references) from None
    except ollama_client.OllamaModelNotFound:
        raise coded(status.HTTP_404_NOT_FOUND, "ollama_model_not_found") from None
    except ollama_client.OllamaUnavailable:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "ollama_unreachable") from None
    return {"ok": True, "model": name}
