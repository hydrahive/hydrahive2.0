"""E3: Media-Backend-Verwaltung (GUI-API) + Verdrahtung.

- CRUD: GET/PUT /api/media-backends (admin-only, Summary ohne Graph-Ballast)
- parse-workflow: ComfyUI-Graph -> Felder + Platzhalter-Vorschläge
- media-models mischt lokale Modelle dazu (gruppiert, category-gefiltert)
"""
from __future__ import annotations


def test_backends_crud_admin_only(client, auth_headers, admin_headers):
    # nicht-admin -> 403
    assert client.get("/api/media-backends", headers=auth_headers).status_code == 403
    # admin -> leer initial
    r = client.get("/api/media-backends", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["media_backends"] == []

    # speichern
    payload = {"media_backends": [{
        "id": "muskeln1", "type": "comfyui", "name": "Muskeln1 ComfyUI",
        "api_base": "http://muskeln1:8189",
        "workflows": [{"id": "ltx", "label": "LTX", "category": "video",
                       "output_node": "SaveAnimatedWEBP",
                       "graph": {"6": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}}},
                       "placeholders": {"prompt": "6.inputs.text"}}],
    }]}
    r = client.put("/api/media-backends", json=payload, headers=admin_headers)
    assert r.status_code == 200 and r.json()["count"] == 1

    # list gibt Summary OHNE den schweren Graph zurück
    r = client.get("/api/media-backends", headers=admin_headers)
    b = r.json()["media_backends"][0]
    assert b["id"] == "muskeln1"
    assert b["workflows"][0]["id"] == "ltx"
    assert "graph" not in b["workflows"][0]  # Ballast entfernt


def test_parse_workflow_suggests_mapping(client, admin_headers):
    graph = {
        "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 20}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "hi"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512}},
    }
    r = client.post("/api/media-backends/parse-workflow",
                    json={"graph": graph}, headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    # Vorschläge aus Heuristik
    assert data["suggestions"]["prompt"] == "6.inputs.text"
    assert data["suggestions"]["seed"] == "3.inputs.seed"
    assert data["suggestions"]["width"] == "5.inputs.width"
    # Nodes gelistet mit skalaren Feldern
    node6 = next(n for n in data["nodes"] if n["id"] == "6")
    assert "text" in node6["inputs"]


def test_parse_workflow_rejects_empty(client, admin_headers):
    r = client.post("/api/media-backends/parse-workflow",
                    json={"graph": {}}, headers=admin_headers)
    assert r.status_code == 400


def test_media_models_merges_local(client, auth_headers, admin_headers, monkeypatch):
    # OpenRouter-Liste leer mocken (kein Key), damit wir nur lokale sehen
    from hydrahive.llm import media_models
    async def _empty():
        return []
    monkeypatch.setattr(media_models, "list_video_models", _empty)

    # lokales ComfyUI-Backend konfigurieren
    payload = {"media_backends": [{
        "id": "m1", "type": "comfyui", "name": "Muskeln1", "api_base": "http://m:8189",
        "workflows": [
            {"id": "ltx-t2v", "label": "LTX Video", "category": "video",
             "graph": {"1": {}}, "durations": [5, 10]},
            {"id": "sdxl", "label": "SDXL Bild", "category": "image", "graph": {"1": {}}},
        ],
    }]}
    client.put("/api/media-backends", json=payload, headers=admin_headers)

    r = client.get("/api/llm/media-models?category=video", headers=auth_headers)
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()["models"]]
    assert "local:m1/ltx-t2v" in ids
    # Bild-Workflow taucht in der Video-Liste NICHT auf
    assert "local:m1/sdxl" not in ids
    # provider-Gruppe gesetzt
    ltx = next(m for m in r.json()["models"] if m["id"] == "local:m1/ltx-t2v")
    assert ltx["provider"] == "Muskeln1" and ltx["local"] is True
