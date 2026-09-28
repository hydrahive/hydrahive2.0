"""Denk-Tiefe (reasoning_effort) wird gegen die Stufen des Modells geprüft.

Vorher: Der Buddy erlaubte per festem Pattern nur low/medium/high, obwohl die
Pill im Chat je nach Modell bis max anbietet. Der Agent-Editor prüfte gar nichts.
"""
from __future__ import annotations

import pytest

from hydrahive.agents._validation import AgentValidationError, validate_reasoning_effort


@pytest.mark.parametrize("effort", ["", "low", "high", "xhigh", "max"])
def test_gueltige_stufen_fuer_opus(effort):
    validate_reasoning_effort(effort, "claude-opus-5-5")


def test_max_bei_altem_claude_ungueltig():
    with pytest.raises(AgentValidationError):
        validate_reasoning_effort("max", "claude-haiku-4-5-20251001")


def test_unbekannte_stufe_ungueltig():
    with pytest.raises(AgentValidationError):
        validate_reasoning_effort("ultra-mega", "claude-opus-5-5")


def test_modell_ohne_tiefe_akzeptiert_nur_leer():
    validate_reasoning_effort("", "ollama/llama3")
    with pytest.raises(AgentValidationError):
        validate_reasoning_effort("low", "ollama/llama3")


def test_buddy_config_nimmt_max_bei_opus(client, auth_headers, monkeypatch):
    monkeypatch.setattr("hydrahive.agents._validation._available_models", lambda: [])
    client.get("/api/buddy/state", headers=auth_headers)
    r = client.patch("/api/buddy/config", headers=auth_headers, json={"model": "claude-opus-5-5"})
    assert r.status_code == 200, r.text
    r = client.patch("/api/buddy/config", headers=auth_headers, json={"reasoning_effort": "max"})
    assert r.status_code == 200, r.text
    assert client.get("/api/buddy/config", headers=auth_headers).json()["reasoning_effort"] == "max"


def test_buddy_config_lehnt_stufe_ab_die_das_modell_nicht_kann(client, auth_headers, monkeypatch):
    monkeypatch.setattr("hydrahive.agents._validation._available_models", lambda: [])
    client.get("/api/buddy/state", headers=auth_headers)
    client.patch("/api/buddy/config", headers=auth_headers, json={"model": "claude-haiku-4-5-20251001"})
    r = client.patch("/api/buddy/config", headers=auth_headers, json={"reasoning_effort": "max"})
    assert r.status_code == 400


def test_agent_patch_prueft_tiefe(client, admin_headers, monkeypatch):
    monkeypatch.setattr("hydrahive.agents._validation._available_models", lambda: [])
    res = client.post("/api/agents", headers=admin_headers, json={
        "type": "specialist", "name": "Tiefe", "llm_model": "claude-haiku-4-5-20251001"})
    aid = res.json()["id"]
    ok = client.patch(f"/api/agents/{aid}", headers=admin_headers, json={"reasoning_effort": "high"})
    assert ok.status_code == 200, ok.text
    bad = client.patch(f"/api/agents/{aid}", headers=admin_headers, json={"reasoning_effort": "max"})
    assert bad.status_code == 400


def test_modellwechsel_setzt_unpassende_tiefe_auf_standard(client, auth_headers, monkeypatch):
    monkeypatch.setattr("hydrahive.agents._validation._available_models", lambda: [])
    client.get("/api/buddy/state", headers=auth_headers)
    client.patch("/api/buddy/config", headers=auth_headers, json={"model": "claude-opus-5-5", "reasoning_effort": "max"})
    r = client.patch("/api/buddy/config", headers=auth_headers, json={"model": "claude-haiku-4-5-20251001"})
    assert r.status_code == 200, r.text
    cfg = client.get("/api/buddy/config", headers=auth_headers).json()
    assert cfg["model"] == "claude-haiku-4-5-20251001" and cfg["reasoning_effort"] == ""
