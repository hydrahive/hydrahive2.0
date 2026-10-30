"""docs/specs/projekt-container-ausfuehrung.md (K1c): verwaltete Agenten (managed_by).

Ein Modul legt einen Agenten an und verwaltet ihn. Werkzeuge, MCP-Server, Projekt, Typ, Systemprompt und Soul sind
dann für alle anderen Wege gesperrt (Route, configure_specialist, interne Aufrufe). Erlaubt bleiben Modell, Fallback,
Denktiefe, Status. Nur das Modul selbst ändert alles – mit seiner Kennung.
"""
from __future__ import annotations

import pytest

from tests.conftest import error_code


@pytest.fixture
def managed(client, admin_headers):
    from hydrahive.agents import config as agent_config
    r = client.post("/api/agents", headers=admin_headers,
                    json={"name": "Labor-Agent", "type": "specialist", "llm_model": "test/model",
                          "tools": ["shell_exec", "file_read"]})
    assert r.status_code in (200, 201), r.text
    aid = r.json()["id"]
    agent_config.set_managed(aid, "hydralabor")
    yield aid


@pytest.mark.parametrize("body", [{"tools": ["shell_exec", "web_browser"]}, {"mcp_servers": ["m1"]},
                                  {"project_id": "anderes"}, {"type": "master"}, {"managed_by": ""},
                                  {"managed_by": "anderes-modul"}])
def test_route_gesperrte_felder(client, admin_headers, managed, body):
    r = client.patch(f"/api/agents/{managed}", headers=admin_headers, json=body)
    assert r.status_code == 409 and error_code(r) == "agent_managed"
    from hydrahive.agents import config as agent_config
    a = agent_config.get(managed)
    assert a["tools"] == ["shell_exec", "file_read"] and a["managed_by"] == "hydralabor"


@pytest.mark.parametrize("body", [{"llm_model": "test/other"}, {"fallback_models": ["test/model"]},
                                  {"status": "disabled"}])
def test_route_erlaubte_felder(client, admin_headers, managed, body):
    r = client.patch(f"/api/agents/{managed}", headers=admin_headers, json=body)
    assert r.status_code == 200, r.text


def test_route_systemprompt_gesperrt(client, admin_headers, managed):
    r = client.put(f"/api/agents/{managed}/system_prompt", headers=admin_headers, json={"prompt": "Ignoriere alles"})
    assert r.status_code == 409 and error_code(r) == "agent_managed"


def test_route_soul_gesperrt(client, admin_headers, managed):
    r = client.put(f"/api/agents/{managed}/soul/identity", headers=admin_headers, json={"content": "x"})
    assert r.status_code == 409 and error_code(r) == "agent_managed"


def test_interner_aufruf_ohne_kennung_gesperrt(managed):
    from hydrahive.agents import config as agent_config
    with pytest.raises(agent_config.AgentManaged):
        agent_config.update(managed, tools=["web_browser"])
    with pytest.raises(agent_config.AgentManaged):
        agent_config.set_system_prompt(managed, "neu")


def test_modul_selbst_darf_alles(managed):
    from hydrahive.agents import config as agent_config
    agent_config.update(managed, tools=["shell_exec"], _managed_by="hydralabor")
    agent_config.set_system_prompt(managed, "Labor-Regeln", _managed_by="hydralabor")
    assert agent_config.get(managed)["tools"] == ["shell_exec"]
    assert agent_config.get_system_prompt(managed) == "Labor-Regeln"


def test_fremdes_modul_darf_nicht(managed):
    from hydrahive.agents import config as agent_config
    with pytest.raises(agent_config.AgentManaged):
        agent_config.update(managed, tools=["shell_exec"], _managed_by="anderes")


def test_nicht_verwalteter_agent_unveraendert(client, admin_headers):
    r = client.post("/api/agents", headers=admin_headers,
                    json={"name": "Normal", "type": "specialist", "llm_model": "test/model", "tools": ["file_read"]})
    aid = r.json()["id"]
    assert client.patch(f"/api/agents/{aid}", headers=admin_headers, json={"tools": ["shell_exec"]}).status_code == 200
    assert client.put(f"/api/agents/{aid}/system_prompt", headers=admin_headers,
                      json={"prompt": "ok"}).status_code == 200


def test_managed_by_nicht_ueber_die_route_setzbar(client, admin_headers):
    r = client.post("/api/agents", headers=admin_headers,
                    json={"name": "N2", "type": "specialist", "llm_model": "test/model"})
    aid = r.json()["id"]
    client.patch(f"/api/agents/{aid}", headers=admin_headers, json={"managed_by": "hydralabor"})
    from hydrahive.agents import config as agent_config
    assert not agent_config.get(aid).get("managed_by")


def test_set_managed_name_geprueft(client, admin_headers):
    from hydrahive.agents import config as agent_config
    r = client.post("/api/agents", headers=admin_headers,
                    json={"name": "N3", "type": "specialist", "llm_model": "test/model"})
    aid = r.json()["id"]
    for bad in ("", "Gross", "a b", "../x"):
        with pytest.raises(ValueError):
            agent_config.set_managed(aid, bad)


def test_configure_specialist_werkzeug_gesperrt(managed):
    """Ein Projekt-Agent kann den verwalteten Spezialisten nicht über sein Werkzeug umbauen."""
    import asyncio
    from pathlib import Path

    from hydrahive.agents import config as agent_config
    from hydrahive.tools import configure_specialist
    from hydrahive.tools.base import ToolContext
    ctx = ToolContext(session_id="s", agent_id="irgendwer", user_id="admin", workspace=Path("/tmp"))
    res = asyncio.run(configure_specialist._execute({"agent_id": managed, "tools": ["web_browser"]}, ctx))
    assert not res.success
    assert agent_config.get(managed)["tools"] == ["shell_exec", "file_read"]


def test_oeffentliche_ansicht_zeigt_verwaltung(client, admin_headers, managed):
    r = client.get(f"/api/agents/{managed}", headers=admin_headers)
    assert r.json().get("managed_by") == "hydralabor"


def test_speichern_mit_ganzem_objekt_und_nur_modell_geaendert(client, admin_headers, managed):
    """Die Einstellungsseite schickt das ganze Objekt (tools, project_id, managed_by …) – unverändert mitgeschickte
    feste Felder dürfen das Speichern eines erlaubten Felds nicht blockieren."""
    full = client.get(f"/api/agents/{managed}", headers=admin_headers).json()
    for k in ("id", "type", "created_at", "updated_at", "created_by"):
        full.pop(k, None)
    full["llm_model"] = "test/other"
    r = client.patch(f"/api/agents/{managed}", headers=admin_headers, json=full)
    assert r.status_code == 200, r.text
    assert r.json()["llm_model"] == "test/other" and r.json()["managed_by"] == "hydralabor"


def test_ganzes_objekt_mit_geaenderten_werkzeugen_bleibt_gesperrt(client, admin_headers, managed):
    full = client.get(f"/api/agents/{managed}", headers=admin_headers).json()
    for k in ("id", "type", "created_at", "updated_at", "created_by"):
        full.pop(k, None)
    full["tools"] = full["tools"] + ["web_browser"]
    r = client.patch(f"/api/agents/{managed}", headers=admin_headers, json=full)
    assert r.status_code == 409 and error_code(r) == "agent_managed"


def test_werkzeuge_in_anderer_reihenfolge_gelten_als_aenderung(managed):
    """Keine Mengen-Logik: jede Abweichung zählt, damit nichts durchrutscht."""
    from hydrahive.agents import config as agent_config
    with pytest.raises(agent_config.AgentManaged):
        agent_config.update(managed, tools=["file_read", "shell_exec"])
