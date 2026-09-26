"""Standard-Modell-Auswahl: gespeicherter Wert muss in der Liste auftauchen.

Hintergrund (26.09.2026): In den LLM-Standardeinstellungen zeigten zwei Felder
"Auswählen…" statt des gespeicherten Modells, obwohl es korrekt lief. Der
gespeicherte Wert und die IDs der Auswahlliste unterschieden sich nur im Präfix:

  Bild       gespeichert openrouter/google/gemini-3.1-flash-image-preview
             Liste       google/gemini-3.1-flash-image-preview
  Embedding  gespeichert text-embedding-3-small
             Liste       openai/text-embedding-3-small

Ein <select> ohne passende <option> zeigt den Platzhalter. Das Backend liefert
deshalb zu jedem Zweck die ID, die in der Liste steht (`selected`).
"""
from __future__ import annotations

from hydrahive.llm import media_models
from hydrahive.llm.model_ids import match_listed_id


def test_image_value_with_openrouter_prefix_matches_bare_listed_id():
    listed = ["google/gemini-3.1-flash-image-preview", "openai/gpt-image-2"]

    assert match_listed_id(
        "openrouter/google/gemini-3.1-flash-image-preview", listed,
    ) == "google/gemini-3.1-flash-image-preview"


def test_embed_value_without_provider_prefix_matches_prefixed_listed_id():
    listed = ["openai/text-embedding-3-small", "nvidia_nim/nvidia/nv-embed-v1"]

    assert match_listed_id("text-embedding-3-small", listed) == "openai/text-embedding-3-small"


def test_exact_match_wins_over_prefix_variant():
    listed = ["text-embedding-3-small", "openai/text-embedding-3-small"]

    assert match_listed_id("text-embedding-3-small", listed) == "text-embedding-3-small"


def test_ambiguous_short_value_is_not_guessed():
    """Zwei Anbieter mit demselben Modellnamen: lieber leer als falsch anzeigen."""
    listed = ["openai/whisper-1", "openrouter/openai/whisper-1"]

    assert match_listed_id("whisper-1", listed) == ""


def test_unknown_value_stays_empty():
    assert match_listed_id("gibt-es-nicht", ["a/b", "c/d"]) == ""
    assert match_listed_id("", ["a/b"]) == ""


def test_local_ids_are_matched_exactly_only():
    """local:-IDs sind Routing-Entscheidungen, dürfen nicht umgedeutet werden."""
    listed = ["local:comfy/flux", "black-forest-labs/flux"]

    assert match_listed_id("local:comfy/flux", listed) == "local:comfy/flux"
    assert match_listed_id("flux", listed) == ""


def test_media_models_endpoint_returns_selected_for_prefixed_image(client, auth_headers, monkeypatch):
    async def fake_image(force=False):
        return [{"id": "google/gemini-3.1-flash-image-preview", "name": "Gemini Flash Image"}]

    monkeypatch.setattr(media_models, "list_image_models", fake_image)
    monkeypatch.setattr(
        "hydrahive.api.routes.llm._configured_media_value",
        lambda cfg_key: "openrouter/google/gemini-3.1-flash-image-preview",
    )

    r = client.get("/api/llm/media-models?category=image", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["selected"] == "google/gemini-3.1-flash-image-preview"


def test_models_endpoint_returns_selected_for_unprefixed_embed(client, auth_headers, monkeypatch):
    from hydrahive.llm import registry
    from hydrahive.llm.registry import ModelEntry

    async def fake_list(modality=None):
        return [ModelEntry(id="openai/text-embedding-3-small", provider="openai",
                           label="openai/text-embedding-3-small", purposes=frozenset({"embed"}))]

    monkeypatch.setattr(registry, "list_models", fake_list)
    monkeypatch.setattr("hydrahive.llm._config.get_default", lambda purpose: "text-embedding-3-small")

    r = client.get("/api/llm/models?modality=embed", headers=auth_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["default"] == "text-embedding-3-small"  # gespeicherter Wert unverändert
    assert body["selected"] == "openai/text-embedding-3-small"  # was die Auswahl anzeigt
