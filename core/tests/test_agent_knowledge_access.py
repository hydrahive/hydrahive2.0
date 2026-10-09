"""Agent-Einstellung knowledge_access: Prüfung + nur Admin darf sie setzen (datamining-access.md §3)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from hydrahive.agents._knowledge_access import normalize
from hydrahive.agents._validation import AgentValidationError


def _make(owner: str, name: str):
    from hydrahive.agents import config as ac
    return ac.create(agent_type="specialist", name=name, llm_model="claude-sonnet-5", tools=[], owner=owner,
                     created_by="x", project_id=None, temperature=0.7, max_tokens=1000, thinking_budget=0)


def _known(pid):
    return {"id": pid} if pid in ("P1", "P2") else None


@pytest.mark.parametrize("bad", [
    "user", {"scope": "alles"}, {"projects": "P1"}, {"projects": [""]}, {"sensitive": "ja"},
    {"x": 1}, {"projects": ["NOPE"]},
])
def test_ungueltige_werte_werden_abgelehnt(bad):
    with patch("hydrahive.projects.config.get", side_effect=_known), pytest.raises(AgentValidationError):
        normalize(bad)


def test_gueltige_werte_und_leeren():
    with patch("hydrahive.projects.config.get", side_effect=_known):
        assert normalize({"scope": "user", "projects": ["P1", "P1", " P2 "], "sensitive": True}) == {
            "scope": "user", "projects": ["P1", "P2"], "sensitive": True}
    assert normalize({}) is None and normalize(None) is None


def test_update_speichert_und_leert():
    from hydrahive.agents import config as ac
    a = _make("till", "t")
    with patch("hydrahive.projects.config.get", side_effect=_known):
        assert ac.update(a["id"], knowledge_access={"projects": ["P2"]})["knowledge_access"] == {"projects": ["P2"]}
    assert "knowledge_access" not in ac.update(a["id"], knowledge_access={})
    with pytest.raises(AgentValidationError):
        ac.update(a["id"], knowledge_access={"scope": "alles"})


def test_nur_admin_darf_ueber_die_api_setzen(client, auth_headers, admin_headers):
    from hydrahive.agents import config as ac
    a = _make("testuser", "t2")
    body = {"knowledge_access": {"scope": "user", "sensitive": True}}
    assert client.patch(f"/api/agents/{a['id']}", json=body, headers=auth_headers).status_code == 403
    assert "knowledge_access" not in ac.get(a["id"])
    r = client.patch(f"/api/agents/{a['id']}", json=body, headers=admin_headers)
    assert r.status_code == 200 and r.json()["knowledge_access"] == {"scope": "user", "sensitive": True}


def test_projekt_agent_kann_es_seinem_spezialisten_nicht_geben():
    from hydrahive.tools._project_authoring import SPECIALIST_RUNTIME_FIELDS
    assert "knowledge_access" not in SPECIALIST_RUNTIME_FIELDS
