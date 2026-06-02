"""#214: Effort-Capability als Backend-SSOT.

Der Non-Admin-Endpoint /api/llm/effort-models liefert die Modell-Präfixe mit
erweitertem Effort (xhigh/max); der Katalog markiert pro Modell supports_effort.
Beides leitet aus EFFORT_PARAM_MODELS ab — keine FE-Duplikation der Liste mehr.
"""
from __future__ import annotations


def test_effort_models_endpoint_returns_prefixes(client, auth_headers):
    r = client.get("/api/llm/effort-models", headers=auth_headers)
    assert r.status_code == 200
    prefixes = r.json()["prefixes"]
    assert "claude-opus-4-8" in prefixes
    assert "claude-sonnet-4-6" in prefixes


def test_effort_models_endpoint_requires_auth(client):
    r = client.get("/api/llm/effort-models")
    assert r.status_code == 401


def test_effort_endpoint_matches_backend_constant(client, auth_headers):
    from hydrahive.llm._anthropic import EFFORT_PARAM_MODELS
    r = client.get("/api/llm/effort-models", headers=auth_headers)
    assert sorted(r.json()["prefixes"]) == sorted(EFFORT_PARAM_MODELS)


def test_catalog_enrich_marks_effort_support():
    from hydrahive.llm.catalog import _enrich
    assert _enrich("anthropic", {"id": "claude-opus-4-8"})["supports_effort"] is True
    assert _enrich("anthropic", {"id": "claude-3-5-sonnet"})["supports_effort"] is False
