"""Zuordnung bestehender Agenten zu Templates (Plan E3 T1, T2, T6-API).

Namen in den Regel-Tests stammen von echten Agenten auf .4 (14.11.2026), ohne Prompts.
"""
from __future__ import annotations

import json

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _migrate, _store

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}
OLD = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch, client):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(_migrate, "_backup_root", lambda: tmp_path / "backups")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    monkeypatch.setattr(tpl._defaults, "_current_system_models", lambda: {})
    _store.reset_cache()
    yield
    _store.reset_cache()


@pytest.mark.parametrize(("name", "expected"), [
    ("hydrahive-security-reviewer", "security"),
    ("cockpit-migration-auditor", "reviewer"),
    ("hydrahive-test-verifier", "reviewer"),
    ("hydrahive-test-speed", "reviewer"),
    ("hydrahive-frontend-engineer", "frontend"),
    ("videoeditor-frontend", "frontend"),
    ("hydrahive-backend-engineer", "backend"),
    ("module-storage-engineer", "backend"),
    ("ISBN Extractor", "klein"),
    ("rom-Gildenarchivar", "recherche"),
])
def test_regeln_spezialisten(name, expected):
    assert _migrate.specialist_template(name) == expected


def test_vorschlag_typen_und_unsicher():
    agents = [
        {"id": "1", "type": "master", "name": "till's Buddy"},
        {"id": "2", "type": "master", "name": "till's Assistant"},
        {"id": "3", "type": "project", "name": "DEV — Projekt-Agent"},
        {"id": "4", "type": "specialist", "name": "rom-Späher"},
        {"id": "5", "type": "specialist", "name": "labor", "managed_by": "hydralabor"},
        {"id": "6", "type": "specialist", "name": "x", "template": "backend"},
    ]
    p = {x["id"]: x for x in _migrate.propose(agents)}
    assert (p["1"]["proposed"], p["2"]["proposed"], p["3"]["proposed"]) == ("buddy", "assistant", "projekt-master")
    assert p["4"]["proposed"] == "recherche" and p["4"]["unsure"] is True
    assert p["5"]["proposed"] == "modul-schnell"
    assert p["6"]["proposed"] == "backend" and p["6"]["current_template"] == "backend"


@pytest.fixture
def two_agents():
    made = [agent_config.create(agent_type="specialist", name=f"mig-{i}", llm_model=OLD, owner="m-anna",
                                created_by="m-anna", temperature=0.7, max_tokens=1000, thinking_budget=0)
            for i in range(2)]
    yield made
    for a in made:
        agent_config.delete(a["id"])


def test_anwenden_mit_sicherung_und_rueckgaengig(two_agents):
    a, b = two_agents
    before = agent_config.get(a["id"])
    res = _migrate.apply({a["id"]: "reviewer", b["id"]: "backend"}, stamp="t1")
    assert res["written"] == 2
    assert agent_config.get(a["id"])["template"] == "reviewer"
    assert agent_config.get(a["id"])["llm_model"] == OLD           # alte Felder bleiben (Rückweg)
    assert _migrate.backups() == ["t1"]
    assert _migrate.undo("t1") == 2
    assert agent_config.get(a["id"]) == before


def test_anwenden_idempotent(two_agents):
    a, _ = two_agents
    _migrate.apply({a["id"]: "reviewer"}, stamp="t2")
    assert _migrate.apply({a["id"]: "reviewer"}, stamp="t3")["written"] == 0


def test_unbekanntes_template_schreibt_nichts(two_agents):
    from hydrahive.agents import AgentValidationError
    a, _ = two_agents
    with pytest.raises(AgentValidationError):
        _migrate.apply({a["id"]: "gibts-nicht"}, stamp="t4")
    assert "template" not in agent_config.get(a["id"])


def test_schreibfehler_rollt_zurueck(two_agents, monkeypatch):
    a, b = two_agents
    from hydrahive.agents import _config_utils
    real = _config_utils.save_atomic
    calls = {"n": 0}

    def flaky(path, data):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("Platte voll")
        real(path, data)
    monkeypatch.setattr(_config_utils, "save_atomic", flaky)
    with pytest.raises(OSError):
        _migrate.apply({a["id"]: "reviewer", b["id"]: "backend"}, stamp="t5")
    monkeypatch.setattr(_config_utils, "save_atomic", real)
    assert "template" not in agent_config.get(a["id"]) and "template" not in agent_config.get(b["id"])


def test_routen_nur_admin(client, auth_headers, admin_headers, two_agents):
    a, _ = two_agents
    assert client.get("/api/agent-templates/bindings/proposal", headers=auth_headers).status_code == 403
    r = client.get("/api/agent-templates/bindings/proposal", headers=admin_headers)
    assert r.status_code == 200 and any(x["id"] == a["id"] for x in r.json()["proposal"])
    body = {"assignments": {a["id"]: "reviewer"}}
    assert client.post("/api/agent-templates/bindings/apply", json=body, headers=auth_headers).status_code == 403
    r = client.post("/api/agent-templates/bindings/apply", json=body, headers=admin_headers)
    assert r.status_code == 200 and r.json()["written"] == 1
    stamp = r.json()["backup"]
    manifest = json.loads((_migrate._backup_root() / stamp / "_manifest.json").read_text())
    assert manifest["written"] == [a["id"]]
    r = client.post(f"/api/agent-templates/bindings/undo/{stamp}", headers=admin_headers)
    assert r.status_code == 200 and "template" not in agent_config.get(a["id"])
    assert client.post("/api/agent-templates/bindings/undo/gibts-nicht", headers=admin_headers).status_code == 404
    assert client.post("/api/agent-templates/bindings/undo/..", headers=admin_headers).status_code in (404, 405)
