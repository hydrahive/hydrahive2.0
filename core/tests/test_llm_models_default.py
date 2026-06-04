"""GET /api/llm/models — default-Feld für Picker-Vorauswahl."""
from __future__ import annotations


def test_models_endpoint_returns_default(client, auth_headers, monkeypatch):
    from hydrahive.llm import registry
    from hydrahive.llm import _config
    async def fake_list(modality=None): return []
    monkeypatch.setattr(registry, "list_models", fake_list)
    monkeypatch.setattr(_config, "get_default", lambda purpose: f"DEF:{purpose}")
    r = client.get("/api/llm/models?modality=chat", headers=auth_headers)
    assert r.status_code == 200 and r.json()["default"] == "DEF:chat"
    r2 = client.get("/api/llm/models", headers=auth_headers)   # kein modality → chat-Default
    assert r2.json()["default"] == "DEF:chat"


def test_models_default_empty_for_unknown_modality(client, auth_headers, monkeypatch):
    from hydrahive.llm import registry
    async def fake_list(modality=None): return []
    monkeypatch.setattr(registry, "list_models", fake_list)
    r = client.get("/api/llm/models?modality=bogus", headers=auth_headers)
    assert r.status_code == 200 and r.json()["default"] == ""
