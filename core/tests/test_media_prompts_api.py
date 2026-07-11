from pathlib import Path

from hydrahive.projects import config as project_config
from hydrahive.settings import settings


def _media_project(client, auth_headers):
    project = project_config.create(name="Prompt Home", description="", members=["testuser"], llm_model="test-model", created_by="admin", init_git=False)
    base = f"/api/projects/{project['id']}/media-projects"
    assert client.post(base, headers=auth_headers, json={"slug": "film", "name": "Film"}).status_code == 201
    return project, base


def test_media_prompt_crud_writes_markdown(client, auth_headers):
    project, media_base = _media_project(client, auth_headers)
    base = f"{media_base}/film/prompts"
    created = client.post(base, headers=auth_headers, json={"slug": "scene-01", "type": "image", "title": "Szene 01", "body": "A cinematic forest", "model": "image-model", "asset_refs": ["characters/hero"]})
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    path = Path(settings.data_dir) / "workspaces" / "projects" / project["id"] / "media" / "film" / "prompts" / "image" / "scene-01.md"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\nversion: 1")
    assert "A cinematic forest" in text

    listed = client.get(base, headers=auth_headers)
    assert [item["slug"] for item in listed.json()] == ["scene-01"]
    fetched = client.get(f"{base}/image/scene-01", headers=auth_headers)
    assert fetched.json()["asset_refs"] == ["characters/hero"]
    patched = client.patch(f"{base}/image/scene-01", headers=auth_headers, json={"status": "executed", "result_refs": ["images/result.png"]})
    assert patched.status_code == 200
    assert patched.json()["result_refs"] == ["images/result.png"]
    assert client.delete(f"{base}/image/scene-01", headers=auth_headers).status_code == 204


def test_media_prompt_rejects_invalid_input_and_missing_project(client, auth_headers):
    _, media_base = _media_project(client, auth_headers)
    base = f"{media_base}/film/prompts"
    assert client.post(base, headers=auth_headers, json={"slug": "../bad", "type": "image", "title": "Bad"}).status_code == 422
    assert client.post(base, headers=auth_headers, json={"slug": "bad", "type": "unknown", "title": "Bad"}).status_code == 422
    missing = f"{media_base}/missing/prompts"
    assert client.get(missing, headers=auth_headers).status_code == 404


def test_media_prompt_requires_project_access(client, auth_headers):
    project = project_config.create(name="Private Prompts", description="", members=[], llm_model="test-model", created_by="admin", init_git=False)
    response = client.get(f"/api/projects/{project['id']}/media-projects/film/prompts", headers=auth_headers)
    assert response.status_code == 403
