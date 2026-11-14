"""Projekt anlegen, wenn das Template ein Modell nennt, das hier nicht verfügbar ist (Mac-User, 14.11.2026).

Vorher: 500 („Modell 'openai-codex/gpt-5.6-terra' ist nicht in der Live-Modell-Liste“), halbe Ordner blieben liegen.
Jetzt: Hauptmodell fehlt → 400 mit Code und Link; Ersatzmodell fehlt → anlegen, Warnung mit Link in der Antwort.
"""
from __future__ import annotations

import pytest

from tests.conftest import error_code, error_params
from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store
from hydrahive.projects import _paths

TERRA = "openai-codex/gpt-5.6-terra"
KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "MiniMax-M3.1-Flash"}          # terra fehlt wie beim Mac-User
LINK = "/admin?section=llm&tab=templates&template=projekt-master"


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN | {TERRA})
    from hydrahive.llm import registry
    monkeypatch.setattr(registry, "known_ids", lambda: KNOWN)
    _store.reset_cache()
    yield
    _store.reset_cache()


def _chain(*models):
    t = dict(tpl.get("projekt-master") or {})            # vorher lesen: get() im mutate()-Block sperrt sich selbst
    with _store.mutate() as d:
        d["templates"]["projekt-master"] = {**d["templates"].get("projekt-master", t), "chain": list(models)}
    _store.reset_cache()


def _project_dirs() -> set[str]:
    roots = [_paths.projects_root(), _paths.workspace_path("x").parent]
    return {p.name for r in roots if r.exists() for p in r.iterdir()}


def test_ersatzmodell_fehlt_projekt_wird_trotzdem_angelegt_mit_warnung(client, admin_headers):
    _chain("claude-opus-5-5", TERRA, "MiniMax-M3.1-Flash")
    r = client.post("/api/projects", json={"name": "Mac-Probe", "template": "projekt-master"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    agent = agent_config.get(body["agent_id"])
    assert agent["template"] == "projekt-master"
    assert body["warnings"] == [{"code": "template_fallback_unavailable", "template": "projekt-master",
                                 "model": TERRA, "link": LINK}]


def test_ohne_probleme_keine_warnungen(client, admin_headers):
    _chain("claude-opus-5-5", "claude-sonnet-5")
    r = client.post("/api/projects", json={"name": "Sauber", "template": "projekt-master"}, headers=admin_headers)
    assert r.status_code == 201 and r.json()["warnings"] == []


def test_hauptmodell_fehlt_400_mit_code_und_link_statt_500(client, admin_headers):
    _chain(TERRA, "claude-sonnet-5")
    before = _project_dirs()
    r = client.post("/api/projects", json={"name": "Mac-Probe-2", "template": "projekt-master"}, headers=admin_headers)
    assert r.status_code == 400, r.text
    assert error_code(r) == "template_primary_unavailable"
    assert error_params(r) == {"template": "projekt-master", "model": TERRA, "link": LINK}
    assert _project_dirs() == before                                    # nichts halb angelegt


def test_anderer_agentenfehler_wird_400_statt_500(client, admin_headers, monkeypatch):
    from hydrahive.agents import AgentValidationError

    def boom(**_kw):
        raise AgentValidationError("tools muss eine Liste sein")
    monkeypatch.setattr(agent_config, "create", boom)
    before = _project_dirs()
    r = client.post("/api/projects", json={"name": "Kaputt", "template": "projekt-master"}, headers=admin_headers)
    assert r.status_code == 400 and error_code(r) == "project_agent_invalid"
    assert error_params(r) == {"message": "tools muss eine Liste sein"}
    assert _project_dirs() == before


def test_template_leer_warnung_mit_link(client, admin_headers):
    _chain()
    r = client.post("/api/projects", json={"name": "LeerTpl", "template": "projekt-master",
                                           "llm_model": "claude-sonnet-5"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["warnings"] == [{"code": "template_not_configured", "template": "projekt-master",
                                     "model": "", "link": LINK}]


def test_ersatzmodell_unbekannt_bei_agent_update_nur_warnung():
    from hydrahive.agents import _validation
    assert _validation.unknown_fallback_models(["claude-sonnet-5", TERRA, TERRA]) == [TERRA]
    with pytest.raises(_validation.AgentValidationError):
        _validation.unknown_fallback_models(["claude-sonnet-5", ""])              # Form-Fehler bleiben hart


def test_warnungen_stehen_nicht_in_der_projektdatei(client, admin_headers):
    import json
    _chain("claude-opus-5-5", TERRA)
    pid = client.post("/api/projects", json={"name": "Datei", "template": "projekt-master"},
                      headers=admin_headers).json()["id"]
    saved = json.loads(_paths.config_path(pid).read_text(encoding="utf-8"))
    assert "warnings" not in saved
    assert "warnings" not in client.get(f"/api/projects/{pid}", headers=admin_headers).json()
