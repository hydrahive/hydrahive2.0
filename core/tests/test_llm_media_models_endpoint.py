"""GET /api/llm/media-models — Live-Liste je Media-Kategorie (require_auth)."""
from __future__ import annotations


def test_media_models_video(client, auth_headers, monkeypatch):
    from hydrahive.llm import media_models

    async def fake_video(force=False):
        return [{"id": "google/veo-3.1", "name": "Veo 3.1"},
                {"id": "openai/sora-2-pro", "name": "Sora 2 Pro"}]

    monkeypatch.setattr(media_models, "list_video_models", fake_video)
    monkeypatch.setattr(media_models, "get_media_model", lambda cat, config=None: "google/veo-3.1")

    r = client.get("/api/llm/media-models?category=video", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["default"] == "google/veo-3.1"
    ids = [m["id"] for m in body["models"]]
    assert "openai/sora-2-pro" in ids


def test_media_models_image(client, auth_headers, monkeypatch):
    from hydrahive.llm import media_models

    async def fake_image(force=False):
        return [{"id": "openai/gpt-image-2", "name": "GPT Image 2"}]

    monkeypatch.setattr(media_models, "list_image_models", fake_image)
    monkeypatch.setattr(media_models, "get_media_model", lambda cat, config=None: "x")

    r = client.get("/api/llm/media-models?category=image", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["models"][0]["id"] == "openai/gpt-image-2"


def test_media_models_audio_uses_music_key(client, auth_headers, monkeypatch):
    from hydrahive.llm import media_models

    seen = {}

    async def fake_audio(force=False):
        return [{"id": "google/lyria-3-pro-preview", "name": "Lyria"}]

    def fake_default(cat, config=None):
        seen["cat"] = cat
        return "google/lyria-3-pro-preview"

    monkeypatch.setattr(media_models, "list_audio_models", fake_audio)
    monkeypatch.setattr(media_models, "get_media_model", fake_default)

    r = client.get("/api/llm/media-models?category=audio", headers=auth_headers)
    assert r.status_code == 200
    # audio-Kategorie mappt auf den Config-Key 'music'
    assert seen["cat"] == "music"


def test_media_models_unknown_category_400(client, auth_headers):
    r = client.get("/api/llm/media-models?category=quatsch", headers=auth_headers)
    assert r.status_code == 400


def test_media_models_needs_auth(client):
    assert client.get("/api/llm/media-models?category=video").status_code == 401
