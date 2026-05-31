"""A4: media_models im LlmConfig-Modell (GET/PUT /api/llm persistiert es).

Import von routes.llm bewusst LAZY in den Funktionen — ein Modul-Level-Import
würde beim Collecten (vor dem session-autouse setup_test_env) Settings-Pfade
cachen und die DB-Tests pollute.
"""
from __future__ import annotations


def test_media_models_durch_model_dump():
    from hydrahive.api.routes.llm import LlmConfig
    cfg = LlmConfig(
        providers=[],
        default_model="x",
        media_models={"image": "openai/gpt-5-image-mini",
                      "music": "google/lyria-3-pro-preview"},
    )
    data = cfg.model_dump()
    assert data["media_models"]["image"] == "openai/gpt-5-image-mini"
    assert data["media_models"]["music"] == "google/lyria-3-pro-preview"


def test_media_models_default_leer():
    from hydrahive.api.routes.llm import LlmConfig
    assert LlmConfig().model_dump()["media_models"] == {}
