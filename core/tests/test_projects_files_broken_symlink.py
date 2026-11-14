"""Workspace-Dateiliste: ein kaputter Eintrag darf nicht die ganze Liste lahmlegen.

Befund 14.11.2026: Ein toter Symlink `node_modules -> ../../../../hydrahive2/frontend/node_modules`
im Projekt-Workspace ließ `GET /api/projects/{id}/files` mit 500 abbrechen (`item.stat()` →
FileNotFoundError). Das Panel zeigte nur „Workspace konnte nicht geladen werden.“
"""
from __future__ import annotations

import os

from hydrahive.projects._paths import workspace_path


def _project(client, admin_headers) -> str:
    r = client.post("/api/projects", json={"name": "SymlinkProj", "llm_model": "claude-sonnet-4-6"},
                    headers=admin_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_broken_symlink_does_not_break_listing(client, admin_headers):
    pid = _project(client, admin_headers)
    ws = workspace_path(pid)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "ok.txt").write_text("hallo")
    (ws / "ordner").mkdir()
    os.symlink("../gibt-es-nicht/node_modules", ws / "node_modules")

    r = client.get(f"/api/projects/{pid}/files", headers=admin_headers)

    assert r.status_code == 200
    by_name = {e["name"]: e for e in r.json()["entries"]}
    assert by_name["ok.txt"]["type"] == "file"
    assert by_name["ok.txt"]["size"] == 5
    assert by_name["ordner"]["type"] == "dir"
    # Kaputter Link bleibt sichtbar (man soll ihn finden und löschen können), aber ohne Größe/Datum-Crash.
    assert by_name["node_modules"]["type"] == "file"
    assert by_name["node_modules"]["size"] is None
    assert by_name["node_modules"]["broken"] is True


def test_intact_symlink_to_dir_is_listed_as_dir(client, admin_headers, tmp_path):
    pid = _project(client, admin_headers)
    ws = workspace_path(pid)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "echt").mkdir()
    os.symlink("echt", ws / "link")

    r = client.get(f"/api/projects/{pid}/files", headers=admin_headers)

    assert r.status_code == 200
    by_name = {e["name"]: e for e in r.json()["entries"]}
    assert by_name["link"]["type"] == "dir"
    assert "broken" not in by_name["link"]
