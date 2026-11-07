from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from hydrahive.api.routes._git_helpers import project_or_404, repo_path_or_404
from hydrahive.db import init_db
from hydrahive.projects import _git_ops
from hydrahive.projects import config as project_config
from hydrahive.projects import execution
from hydrahive.projects._paths import workspace_path
from hydrahive.projects.public_view import public_view


@pytest.fixture(autouse=True)
def database():
    init_db()


def test_host_git_api_ist_fuer_containerprojekt_gesperrt(monkeypatch) -> None:
    project = project_config.create("Container Git", members=[], llm_model="test-model", created_by="admin")
    monkeypatch.setattr(execution, "_container_exists", lambda _name: True)
    execution.set_container(project["id"], "hh-vibe-test", actor="admin")
    try:
        with pytest.raises(HTTPException) as exc:
            project_or_404(project["id"], "admin", "admin", required="write")
        assert exc.value.status_code == 409
        assert exc.value.detail["code"] == "git_container_project"
    finally:
        project_config.delete(project["id"])


def test_repo_symlink_darf_nicht_aus_projektworkspace_fuehren(tmp_path) -> None:
    project = project_config.create("Symlink Git", members=[], llm_model="test-model", created_by="admin")
    workspace = workspace_path(project["id"])
    outside = tmp_path / "outside"
    (outside / ".git").mkdir(parents=True)
    (workspace / "escape").symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(HTTPException) as exc:
            repo_path_or_404(project["id"], "escape")
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "git_repo_not_found"
    finally:
        project_config.delete(project["id"])


def test_git_metadaten_symlink_darf_nicht_aus_projektworkspace_fuehren(tmp_path) -> None:
    project = project_config.create("Gitdir Symlink", members=[], llm_model="test-model", created_by="admin")
    workspace = workspace_path(project["id"])
    outside_git = tmp_path / "outside-git"
    outside_git.mkdir()
    repo = workspace / "repo"
    repo.mkdir()
    (repo / ".git").symlink_to(outside_git, target_is_directory=True)
    try:
        with pytest.raises(HTTPException) as exc:
            repo_path_or_404(project["id"], "repo")
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "git_repo_not_found"
    finally:
        project_config.delete(project["id"])


def test_gitdir_datei_bleibt_auf_projektworkspace_beschraenkt(tmp_path) -> None:
    project = project_config.create("Gitdir Datei", members=[], llm_model="test-model", created_by="admin")
    workspace = workspace_path(project["id"])
    repo = workspace / "repo"
    repo.mkdir()
    inside_git = workspace / "git-metadata"
    inside_git.mkdir()
    marker = repo / ".git"
    try:
        marker.write_text("gitdir: ../git-metadata\n", encoding="utf-8")
        assert repo_path_or_404(project["id"], "repo") == repo.resolve()

        outside_git = tmp_path / "outside-gitdir"
        outside_git.mkdir()
        marker.write_text(f"gitdir: {outside_git}\n", encoding="utf-8")
        with pytest.raises(HTTPException) as exc:
            repo_path_or_404(project["id"], "repo")
        assert exc.value.detail["code"] == "git_repo_not_found"
    finally:
        project_config.delete(project["id"])


def test_public_view_zeigt_nur_den_ausfuehrungsmodus() -> None:
    view = public_view(
        {
            "id": "p1",
            "execution": {"mode": "container", "container": "hh-vibe-test", "workdir": "/work", "user": 1000},
        }
    )

    assert view["execution_mode"] == "container"
    assert "execution" not in view
    assert "hh-vibe-test" not in str(view)


def test_host_git_deaktiviert_hooks_und_fsmonitor(tmp_path, monkeypatch) -> None:
    seen = {}

    def fake_run(args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(_git_ops.subprocess, "run", fake_run)

    ok, _, _ = _git_ops._runx(tmp_path, "status")

    assert ok is True
    assert seen["args"][:5] == [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
    ]
    assert seen["args"][-1] == "status"
