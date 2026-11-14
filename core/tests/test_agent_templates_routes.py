"""API der Agenten-Templates: Rechte und Abläufe (Plan E2 T4)."""
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store

KNOWN = {"claude-opus-5-5", "claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"}


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: KNOWN)
    from hydrahive.llm import registry
    monkeypatch.setattr(registry, "known_ids", lambda: KNOWN)
    _store.reset_cache()
    yield
    _store.reset_cache()


BODY = {"label": "Übersetzer", "group": "specialists", "chain": ["claude-sonnet-5", "openai-codex/gpt-5.6-terra"],
        "budget": {"max_iterations": 8, "max_tokens": 4096, "timeout_seconds": 120}}


def test_nutzer_darf_lesen(client, auth_headers):
    r = client.get("/api/agent-templates", headers=auth_headers)
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()["templates"]}
    assert "projekt-master" in ids
    pm = next(t for t in r.json()["templates"] if t["id"] == "projekt-master")
    assert pm["health"]["state"] == "green"


@pytest.mark.parametrize(("method", "path"), [
    ("put", "/api/agent-templates/uebersetzer"),
    ("post", "/api/agent-templates/uebersetzer/preview"),
    ("post", "/api/agent-templates/buddy/test"),
    ("post", "/api/agent-templates/buddy/revert/1"),
    ("delete", "/api/agent-templates/buddy"),
    ("get", "/api/agent-templates/bindings"),
])
def test_nutzer_darf_nicht_schreiben(client, auth_headers, method, path):
    kw = {"json": BODY} if method in ("put", "post") else {}
    r = getattr(client, method)(path, headers=auth_headers, **kw)
    assert r.status_code == 403


def test_admin_legt_an_aendert_und_holt_zurueck(client, admin_headers):
    r = client.put("/api/agent-templates/uebersetzer", json=BODY, headers=admin_headers)
    assert r.status_code == 200 and r.json()["revision"] == 1
    r = client.put("/api/agent-templates/uebersetzer", json={**BODY, "label": "Neu"}, headers=admin_headers)
    assert r.json()["revision"] == 2
    d = client.get("/api/agent-templates/uebersetzer", headers=admin_headers).json()
    assert [h["revision"] for h in d["history"]] == [1]
    r = client.post("/api/agent-templates/uebersetzer/revert/1", headers=admin_headers)
    assert r.status_code == 200 and r.json()["label"] == "Übersetzer"


def test_ungueltig_gibt_fehlercode(client, admin_headers):
    r = client.put("/api/agent-templates/uebersetzer", json={**BODY, "chain": []}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "chain_empty"


def test_unbekannt_404(client, auth_headers):
    assert client.get("/api/agent-templates/gibts-nicht", headers=auth_headers).status_code == 404


def test_preview_listet_betroffene(client, admin_headers):
    a = agent_config.create(agent_type="specialist", name="tpl-preview", llm_model="claude-sonnet-5",
                            owner="admin", created_by="admin", temperature=0.7, max_tokens=1000,
                            thinking_budget=0)
    agent_config.update(a["id"], template="reviewer")
    try:
        body = {**tpl.get("reviewer")}
        body["budget"] = {**body["budget"], "max_iterations": 120}
        body = {k: body[k] for k in ("label", "group", "chain", "budget", "reply")}
        r = client.post("/api/agent-templates/reviewer/preview", json=body, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["changed"] == ["budget"]
        assert [x["id"] for x in r.json()["affected"]] == [a["id"]]
    finally:
        agent_config.delete(a["id"])


def test_loeschen_mit_gebundenen_409(client, admin_headers):
    client.put("/api/agent-templates/uebersetzer", json=BODY, headers=admin_headers)
    a = agent_config.create(agent_type="specialist", name="tpl-del", llm_model="claude-sonnet-5",
                            owner="admin", created_by="admin", temperature=0.7, max_tokens=1000,
                            thinking_budget=0)
    agent_config.update(a["id"], template="uebersetzer")
    try:
        r = client.delete("/api/agent-templates/uebersetzer", headers=admin_headers)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "template_in_use"
    finally:
        agent_config.delete(a["id"])
    assert client.delete("/api/agent-templates/uebersetzer", headers=admin_headers).status_code == 200


def test_testlauf_je_stufe(client, admin_headers, monkeypatch):
    from hydrahive.llm import client as llm_client

    async def fake_complete(messages, model=None, **kw):
        if model == "claude-sonnet-5":
            raise RuntimeError("Error 429: Too Many Requests")
        return "OK"
    monkeypatch.setattr(llm_client, "complete", fake_complete)
    r = client.post("/api/agent-templates/buddy/test", json={}, headers=admin_headers)
    assert r.status_code == 200
    res = r.json()["results"]
    assert res[0] == {"model": "claude-sonnet-5", "ok": False, "reason": "rate_limit",
                      "message": "Error 429: Too Many Requests"}
    assert all(x["ok"] for x in res[1:])


def test_ampel_rot_bei_unbekanntem_modell(client, admin_headers):
    client.put("/api/agent-templates/uebersetzer", json={**BODY, "chain": ["gibts/nicht"]}, headers=admin_headers)
    d = client.get("/api/agent-templates/uebersetzer", headers=admin_headers).json()
    assert d["health"]["state"] == "red" and d["health"]["unknown_models"] == ["gibts/nicht"]
