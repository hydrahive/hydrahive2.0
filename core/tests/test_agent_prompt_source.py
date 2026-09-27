"""System-Prompt-Quelle: Soul ersetzt system_prompt.md komplett.

Die API muss melden, woher der wirksame Prompt kommt, damit der
Prompt-Reiter nicht still ins Leere speichert (MED-1).
"""
from __future__ import annotations


def _create_agent(client, admin_headers) -> str:
    res = client.post("/api/agents", headers=admin_headers, json={
        "type": "specialist", "name": "Soul Bot", "llm_model": "claude-haiku-4-5-20251001",
    })
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_quelle_ist_prompt_ohne_soul(client, admin_headers):
    agent_id = _create_agent(client, admin_headers)
    client.put(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers, json={"prompt": "Eigener Prompt"})
    res = client.get(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers)
    assert res.status_code == 200
    assert res.json() == {"prompt": "Eigener Prompt", "source": "prompt"}


def test_quelle_ist_soul_wenn_soul_datei_existiert(client, admin_headers):
    agent_id = _create_agent(client, admin_headers)
    client.put(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers, json={"prompt": "Wird ignoriert"})
    res = client.put(f"/api/agents/{agent_id}/soul/identity", headers=admin_headers, json={"content": "Ich bin Soul"})
    assert res.status_code == 200
    body = client.get(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers).json()
    assert body["source"] == "soul"
    assert body["prompt"] == "Ich bin Soul"


def test_leere_soul_datei_zaehlt_nicht(client, admin_headers):
    agent_id = _create_agent(client, admin_headers)
    client.put(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers, json={"prompt": "Bleibt aktiv"})
    client.put(f"/api/agents/{agent_id}/soul/identity", headers=admin_headers, json={"content": "   "})
    body = client.get(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers).json()
    assert body == {"prompt": "Bleibt aktiv", "source": "prompt"}


def test_prompt_speichern_bei_aktiver_soul_wird_abgelehnt(client, admin_headers):
    agent_id = _create_agent(client, admin_headers)
    client.put(f"/api/agents/{agent_id}/soul/behavior", headers=admin_headers, json={"content": "Soul aktiv"})
    res = client.put(f"/api/agents/{agent_id}/system_prompt", headers=admin_headers, json={"prompt": "ins Leere"})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "soul_active"
