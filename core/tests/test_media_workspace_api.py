from hydrahive.projects import config as project_config


def _base(client, auth_headers):
    project = project_config.create(name="Production", members=["testuser"], llm_model="test", created_by="admin")
    media = f"/api/projects/{project['id']}/media-projects"
    assert client.post(media, headers=auth_headers, json={"slug": "film", "name": "Film"}).status_code == 201
    return f"{media}/film"


def test_screenplay_persists_act_scene_shot(client, auth_headers):
    base = _base(client, auth_headers)
    payload = {"title": "Film", "logline": "Test", "acts": [{"id": "act-1", "title": "Akt 1", "scenes": [{"id": "scene-1", "title": "Ankunft", "shots": [{"id": "shot-1", "title": "Totale", "duration": 5, "asset_ids": ["frame"]}]}]}]}
    assert client.put(f"{base}/screenplay", headers=auth_headers, json=payload).status_code == 200
    fetched = client.get(f"{base}/screenplay", headers=auth_headers).json()
    assert fetched["acts"][0]["scenes"][0]["shots"][0]["asset_ids"] == ["frame"]


def test_agent_context_and_timeline_persist(client, auth_headers):
    base = _base(client, auth_headers)
    context = {"note": "Shots prüfen", "active_scene_id": "scene-1", "asset_ids": ["frame"], "prompt_draft": "Prompt"}
    assert client.put(f"{base}/agent-context", headers=auth_headers, json=context).status_code == 200
    assert client.get(f"{base}/agent-context", headers=auth_headers).json()["note"] == "Shots prüfen"
    timeline = {"fps": 25, "width": 1920, "height": 1080, "tracks": [{"id": "video-1", "name": "Video", "kind": "video", "clips": [{"id": "clip-1", "asset_id": "frame", "start": 0, "duration": 5, "source_in": 0}]}]}
    assert client.put(f"{base}/timeline", headers=auth_headers, json=timeline).status_code == 200
    assert client.get(f"{base}/timeline", headers=auth_headers).json()["tracks"][0]["clips"][0]["duration"] == 5


def test_timeline_rejects_duplicate_clip_ids(client, auth_headers):
    base = _base(client, auth_headers)
    clip = {"id": "same", "asset_id": "a", "start": 0, "duration": 1}
    payload = {"tracks": [{"id": "one", "kind": "video", "clips": [clip]}, {"id": "two", "kind": "audio", "clips": [clip]}]}
    assert client.put(f"{base}/timeline", headers=auth_headers, json=payload).status_code == 422
