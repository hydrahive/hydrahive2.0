from pathlib import Path

from hydrahive.projects import config as project_config
from hydrahive.settings import settings


def _project(admin_headers):
    return project_config.create(name="Media Home", description="", members=["testuser"], llm_model="test-model", created_by="admin", init_git=False)


def test_media_project_crud_creates_workspace(client, auth_headers, admin_headers):
    project = _project(admin_headers)
    base = f"/api/projects/{project['id']}/media-projects"
    created = client.post(base, headers=auth_headers, json={"slug": "mein-film", "name": "Mein Film", "description": "Test"})
    assert created.status_code == 201

    root = Path(settings.data_dir) / "workspaces" / "projects" / project["id"] / "media" / "mein-film"
    assert (root / "media-project.json").is_file()
    assert (root / "project.md").is_file()
    assert all((root / name).is_dir() for name in ("prompts", "assets", "images", "video", "audio", "timeline", "exports"))

    listed = client.get(base, headers=auth_headers)
    assert [item["slug"] for item in listed.json()] == ["mein-film"]
    patched = client.patch(f"{base}/mein-film", headers=auth_headers, json={"name": "Neuer Titel"})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Neuer Titel"
    assert client.delete(f"{base}/mein-film", headers=auth_headers).status_code == 204
    assert client.get(f"{base}/mein-film", headers=auth_headers).status_code == 404


def test_media_project_rejects_invalid_slug(client, auth_headers, admin_headers):
    project = _project(admin_headers)
    response = client.post(f"/api/projects/{project['id']}/media-projects", headers=auth_headers, json={"slug": "../escape", "name": "Bad"})
    assert response.status_code == 422


def test_media_project_requires_project_access(client, auth_headers, admin_headers):
    project = project_config.create(name="Private", description="", members=[], llm_model="test-model", created_by="admin", init_git=False)
    response = client.get(f"/api/projects/{project['id']}/media-projects", headers=auth_headers)
    assert response.status_code == 403
