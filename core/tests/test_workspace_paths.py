from __future__ import annotations
import pytest
from pathlib import Path
from hydrahive.workspace._paths import resolve_in_workspace, WorkspacePathError


def test_resolves_relative_path(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.txt").write_text("x")
    result = resolve_in_workspace(tmp_path, "sub/f.txt")
    assert result == (tmp_path / "sub" / "f.txt").resolve()


def test_rejects_traversal(tmp_path: Path):
    with pytest.raises(WorkspacePathError):
        resolve_in_workspace(tmp_path, "../../etc/passwd")


def test_rejects_absolute_escape(tmp_path: Path):
    with pytest.raises(WorkspacePathError):
        resolve_in_workspace(tmp_path, "/etc/passwd")


def test_empty_path_returns_root(tmp_path: Path):
    assert resolve_in_workspace(tmp_path, "") == tmp_path.resolve()
