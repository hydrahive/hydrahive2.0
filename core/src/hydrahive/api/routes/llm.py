from __future__ import annotations

import json

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from typing import Annotated

from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.llm import _config
from hydrahive.llm import client as llm_client
from hydrahive.llm import registry
from hydrahive.llm._codex_usage import fetch_usage as fetch_codex_usage
from hydrahive.llm._minimax_usage import fetch_usage as fetch_minimax_usage
from hydrahive.llm._oauth_usage import get_oauth_rate_limits
from hydrahive.llm._openrouter_credits import fetch_credits as fetch_openrouter_credits
from hydrahive.settings import settings

router = APIRouter(prefix="/api/llm", tags=["llm"])


class LlmProvider(BaseModel):
    # extra="allow": OAuth-Block (oauth.access etc.) wird durchgereicht.
    # Ohne das würde model_dump() den OAuth-Block stillschweigend droppen.
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    api_key: str
    models: list[str]


class LlmConfig(BaseModel):
    providers: list[LlmProvider] = []
    default_model: str = ""
    embed_model: str = ""
    # Aktives Modell pro Media-Kategorie (image/music/tts/transcribe/video).
    # Resolver: hydrahive.llm.media_models.get_media_model
    media_models: dict[str, str] = {}


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
async def update_config(cfg: LlmConfig) -> dict:
    old_model = _load().get("embed_model", "")
    data = cfg.model_dump()
    _save(data)
    from hydrahive.llm import registry
    registry.invalidate()
    new_model = data.get("embed_model", "")
    if new_model != old_model:
        from hydrahive.db import mirror
        await mirror.on_embed_model_change(new_model)
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


@router.get("/minimax/usage")
async def minimax_usage(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """MiniMax token_plan/remains pro Modell. Auch für non-admin sichtbar — nur Quota-Info."""
    return await fetch_minimax_usage()


@router.get("/anthropic/rate-limits")
def anthropic_rate_limits(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Anthropic OAuth Rate-Limits. Für alle User sichtbar — zeigt 5h/7d Utilization."""
    return get_oauth_rate_limits()


@router.get("/codex/usage")
async def codex_usage(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Codex Plan-Usage (5h/7d) aus der ChatGPT-OAuth. Ausgeblendet wenn kein OAuth aktiv."""
    return await fetch_codex_usage()


@router.get("/openrouter/credits")
async def openrouter_credits(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """OpenRouter Restguthaben. Ausgeblendet wenn kein Key gesetzt."""
    return await fetch_openrouter_credits()


@router.get("/effort-models")
def effort_models(_: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    """Modell-Präfixe mit erweitertem Effort (xhigh/max) — SSOT fürs Frontend.

    Leitet aus EFFORT_PARAM_MODELS ab, damit die Effort-Capability nicht im
    Frontend dupliziert (und bei neuen Modellen vergessen) wird (#214).
    """
    from hydrahive.llm._anthropic import EFFORT_PARAM_MODELS
    return {"prefixes": list(EFFORT_PARAM_MODELS)}


@router.get("/effort-levels")
def effort_levels(
    model: str,
    _: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Erlaubte Reasoning-Tiefen für das konkrete Modell."""
    from hydrahive.llm.reasoning_effort import effort_levels_for_model
    return {"levels": list(effort_levels_for_model(model))}


@router.get("/models")
async def list_llm_models(
    modality: str | None = None,
    _: Annotated[tuple[str, str], Depends(require_auth)] = None,
) -> dict:
    """Kanonische Modell-Liste aus der Registry, optional nach Zweck gefiltert.
    Für ALLE Picker (require_auth, nicht admin-only). `default` = konfiguriertes
    Standard-Modell des Zwecks (für die Vorauswahl)."""
    entries = await registry.list_models(modality)
    if modality is None:
        purpose = "chat"
    elif modality in _config._PURPOSE_KEYS:
        purpose = modality
    else:
        purpose = None
    default = _config.get_default(purpose) if purpose else ""
    return {
        "default": default,
        "models": [
            {"id": e.id, "label": e.label, "provider": e.provider,
             "purposes": sorted(e.purposes), "context_window": e.context_window,
             "is_free": e.is_free, "embed_dim": e.embed_dim}
            for e in entries
        ],
    }


# category → (Live-Lister, Config-Key für das aktive Modell)
_MEDIA_CATEGORY_KEY = {"video": "video", "image": "image", "audio": "music"}


@router.get("/media-models")
async def list_media_models(
    category: str,
    _: Annotated[tuple[str, str], Depends(require_auth)] = None,
) -> dict:
    """Live-Liste der Media-Generierungs-Modelle je Kategorie (OpenRouter), für
    Frontend-Picker (Atelier Regie/Video/Audio). `default` = konfiguriertes
    Modell der Kategorie. 5-Min-Cache in media_models. Ohne Key → leere Liste.

    category: 'video' | 'image' | 'audio'.
    """
    from hydrahive.llm import media_models
    cfg_key = _MEDIA_CATEGORY_KEY.get(category)
    if cfg_key is None:
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_category")
    if category == "video":
        models = await media_models.list_video_models()
    elif category == "image":
        models = await media_models.list_image_models()
    else:  # audio
        models = await media_models.list_audio_models()
    return {"default": media_models.get_media_model(cfg_key), "models": models}
