from __future__ import annotations

from hydrahive.api.routes import llm_catalog_ollama


def test_ollama_catalog_is_admin_only(client, auth_headers):
    response = client.get("/api/llm/catalog/ollama", headers=auth_headers)
    assert response.status_code == 403


def test_admin_can_read_ollama_catalog(client, admin_headers, monkeypatch):
    monkeypatch.setattr(llm_catalog_ollama.ollama_manager, "configured_provider", lambda: {"id": "ollama"}, raising=False)

    async def overview(provider):
        return {"connected": True, "families": [], "installed_models": [], "hardware_fit": {"available": False}}

    monkeypatch.setattr(llm_catalog_ollama.ollama_manager, "catalog_overview", overview, raising=False)
    response = client.get("/api/llm/catalog/ollama", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["connected"] is True


def test_pull_rejects_invalid_model_without_starting_job(client, admin_headers, monkeypatch):
    called = False

    async def start(*args):
        nonlocal called
        called = True

    monkeypatch.setattr(llm_catalog_ollama.ollama_lifecycle, "start_pull", start, raising=False)
    response = client.post(
        "/api/llm/catalog/ollama/pulls",
        headers=admin_headers,
        json={"model": "https://evil.invalid/model"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_ollama_model"
    assert called is False


def test_delete_returns_conflict_with_safe_references(client, admin_headers, monkeypatch):
    async def remove(provider, model):
        raise llm_catalog_ollama.ollama_lifecycle.ModelInUse(["Agent: Coder"])

    monkeypatch.setattr(llm_catalog_ollama.ollama_manager, "configured_provider", lambda: {"id": "ollama"}, raising=False)
    monkeypatch.setattr(llm_catalog_ollama.ollama_lifecycle, "delete_model", remove, raising=False)
    response = client.delete("/api/llm/catalog/ollama/models/qwen3:14b", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "ollama_model_in_use",
        "params": {"references": ["Agent: Coder"]},
    }
