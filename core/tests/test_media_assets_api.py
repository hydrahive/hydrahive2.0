from pathlib import Path

from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path


def _setup(client, auth_headers):
    home = project_config.create(name="Media Home", members=["testuser"], llm_model="test", created_by="admin")
    source = project_config.create(name="Asset Source", members=["testuser"], llm_model="test", created_by="admin")
    base = f"/api/projects/{home['id']}/media-projects"
    assert client.post(base, headers=auth_headers, json={"slug": "film", "name": "Film"}).status_code == 201
    source_file = workspace_path(source["id"]) / "atelier" / "gallery" / "frame.png"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"PNG")
    return home, source, f"{base}/film/assets", source_file


def test_cross_project_asset_reference_and_import(client, auth_headers):
    home, source, base, _ = _setup(client, auth_headers)
    body = {"id": "opening-frame", "kind": "image", "source_project_id": source["id"], "rel_path": "atelier/gallery/frame.png", "label": "Opening Frame"}
    created = client.post(base, headers=auth_headers, json=body)
    assert created.status_code == 201
    assert created.json()["read_only"] is True
    assert client.get(base, headers=auth_headers).json()[0]["available"] is True

    imported = client.post(f"{base}/opening-frame/import", headers=auth_headers)
    assert imported.status_code == 200
    assert imported.json()["mode"] == "copy"
    copied = workspace_path(home["id"]) / imported.json()["rel_path"]
    assert copied.read_bytes() == b"PNG"
    assert client.delete(f"{base}/opening-frame", headers=auth_headers).status_code == 204


def test_asset_reference_rejects_traversal(client, auth_headers):
    _, source, base, _ = _setup(client, auth_headers)
    response = client.post(base, headers=auth_headers, json={"id": "escape", "kind": "image", "source_project_id": source["id"], "rel_path": "../config.json", "label": "Bad"})
    assert response.status_code == 400


def test_asset_reference_requires_source_access(client, auth_headers):
    _, _, base, _ = _setup(client, auth_headers)
    private = project_config.create(name="Private Source", members=[], llm_model="test", created_by="admin")
    source_file = workspace_path(private["id"]) / "secret.png"
    source_file.write_bytes(b"secret")
    response = client.post(base, headers=auth_headers, json={"id": "secret", "kind": "image", "source_project_id": private["id"], "rel_path": "secret.png", "label": "Secret"})
    assert response.status_code == 403
