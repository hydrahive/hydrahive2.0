"""GET /api/llm/models — kanonische Modell-Liste aus der Registry (require_auth)."""
from __future__ import annotations


def test_models_endpoint_auth_and_filter(client, auth_headers, monkeypatch):
    from hydrahive.llm import registry
    from hydrahive.llm.registry import ModelEntry

    async def fake_list(modality=None):
        all_ = [
            ModelEntry("openrouter/chatty", "openrouter", "openrouter/chatty", frozenset({"chat"})),
            ModelEntry("hexgrad/kokoro", "openrouter", "hexgrad/kokoro", frozenset({"tts"})),
        ]
        return [m for m in all_ if (modality is None or modality in m.purposes)]

    monkeypatch.setattr(registry, "list_models", fake_list)

    # non-admin user can access (require_auth, not require_admin)
    r = client.get("/api/llm/models", headers=auth_headers)
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["models"]]
    assert "openrouter/chatty" in ids and "hexgrad/kokoro" in ids

    # modality filter works
    r2 = client.get("/api/llm/models?modality=tts", headers=auth_headers)
    assert [m["id"] for m in r2.json()["models"]] == ["hexgrad/kokoro"]
