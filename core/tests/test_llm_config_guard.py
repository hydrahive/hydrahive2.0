"""Schutz der LLM-Einstellungen (gefunden 20.10.2026 beim Test von „Lehren“): Die Admin-Seite startet mit einem leeren
Platzhalter (keine Anbieter); wurde ein Feld geändert, bevor die echten Einstellungen geladen waren, überschrieb PUT
/api/llm alles mit leer. Jetzt lehnt der Server das ab, und einzelne Zwecke lassen sich gezielt setzen."""
from __future__ import annotations

import json

from hydrahive.settings import settings


def _seed() -> dict:
    data = {"providers": [{"id": "openrouter", "name": "OpenRouter", "api_key": "k", "models": []}],
            "default_model": "openrouter/x", "embed_model": "", "media_models": {"image": "openrouter/img"},
            "media_backends": [{"id": "wks", "type": "comfyui", "api_base": "http://wks:8189", "workflows": []}]}
    settings.llm_config.write_text(json.dumps(data))
    return data


def test_empty_placeholder_cannot_wipe_providers(client, admin_headers) -> None:
    before = _seed()
    r = client.put("/api/llm", headers=admin_headers, json={"providers": [], "default_model": "", "embed_model": "",
                                                             "media_models": {}, "lessons_model": "off"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "llm_config_would_clear"
    assert json.loads(settings.llm_config.read_text()) == before                     # nichts verändert


def test_removing_last_provider_needs_explicit_flag(client, admin_headers) -> None:
    _seed()
    cur = client.get("/api/llm", headers=admin_headers).json()
    r = client.put("/api/llm?allow_clear=true", headers=admin_headers, json={**cur, "providers": []})
    assert r.status_code == 200 and json.loads(settings.llm_config.read_text())["providers"] == []


def test_normal_save_still_works(client, admin_headers) -> None:
    _seed()
    cur = client.get("/api/llm", headers=admin_headers).json()
    r = client.put("/api/llm", headers=admin_headers, json={**cur, "lessons_model": "off"})
    assert r.status_code == 200 and json.loads(settings.llm_config.read_text())["lessons_model"] == "off"


def test_set_one_purpose_keeps_everything_else(client, admin_headers) -> None:
    before = _seed()
    r = client.put("/api/llm/default/lessons", headers=admin_headers, json={"model": "off"})
    assert r.status_code == 200, r.text
    after = json.loads(settings.llm_config.read_text())
    assert after["lessons_model"] == "off"
    assert {k: v for k, v in after.items() if k != "lessons_model"} == before
    r = client.put("/api/llm/default/image", headers=admin_headers, json={"model": "openrouter/neu"})
    assert r.status_code == 200 and json.loads(settings.llm_config.read_text())["media_models"]["image"] == "openrouter/neu"
    assert json.loads(settings.llm_config.read_text())["providers"] == before["providers"]


def test_set_one_purpose_rejects_unknown_purpose_and_non_admin(client, admin_headers, auth_headers) -> None:
    _seed()
    assert client.put("/api/llm/default/magic", headers=admin_headers, json={"model": "x"}).status_code == 400
    assert client.put("/api/llm/default/lessons", headers=auth_headers, json={"model": "x"}).status_code == 403
    assert client.put("/api/llm/default/lessons", headers=admin_headers, json={"model": "x" * 300}).status_code == 422
