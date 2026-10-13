"""System-Backup und Restore lassen das System-Archiv aus (Spec archiv-system.md, „Ort und Einrichtung“).

Das Archiv liegt standardmäßig unter workspaces/archive. workspaces/ wird komplett gesichert und beim Restore
ersetzt. Ohne Ausnahme stünde das ganze Archiv in jedem Backup (Backup im Backup), und ein Restore würde das
Archiv durch einen alten Stand ersetzen – also genau die Daten löschen, die das Archiv retten soll.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.backup import _paths
from hydrahive.settings import settings


@pytest.fixture
def ws(tmp_path, monkeypatch) -> Path:
    w = tmp_path / "workspaces"
    (w / "archive" / "agents").mkdir(parents=True)
    (w / "projects" / "p1" / "archive").mkdir(parents=True)
    monkeypatch.setattr(settings, "workspaces_dir", w, raising=False)
    monkeypatch.setattr(settings, "config_dir", tmp_path / "config", raising=False)
    return w


def test_system_archive_not_in_backup(ws) -> None:
    assert _paths.is_excluded(ws / "archive")
    assert _paths.is_excluded(ws / "archive" / "agents" / "paket.tar.gz")


def test_folders_named_archive_in_projects_stay_in_backup(ws) -> None:
    """Nur genau der System-Archiv-Ordner fällt raus, nicht jeder Ordner namens „archive“."""
    assert not _paths.is_excluded(ws / "projects" / "p1" / "archive")
    assert not _paths.is_excluded(ws / "projects" / "p1" / "archive" / "notiz.md")
    assert not _paths.is_excluded(ws / "archive-alt")


def test_relocated_archive_inside_workspaces_also_excluded(ws, tmp_path) -> None:
    import json
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "archive.json").write_text(json.dumps({"local_dir": str(ws / "sicherung")}))
    assert _paths.is_excluded(ws / "sicherung" / "x.tar.gz")
    assert not _paths.is_excluded(ws / "archive" / "x.tar.gz")


def test_restore_keeps_live_archive(ws, tmp_path) -> None:
    """Restore ersetzt workspaces/, aber das vorhandene Archiv bleibt unverändert stehen."""
    from hydrahive.backup import restore
    (ws / "archive" / "agents" / "paket.tar.gz").write_bytes(b"live")
    (ws / "projects" / "p1" / "alt.txt").write_text("alt")
    src = tmp_path / "extract" / "workspaces"
    (src / "projects" / "p1").mkdir(parents=True)
    (src / "projects" / "p1" / "neu.txt").write_text("neu")

    restore._atomic_replace_dir(src, ws)

    assert (ws / "archive" / "agents" / "paket.tar.gz").read_bytes() == b"live"
    assert (ws / "projects" / "p1" / "neu.txt").read_text() == "neu"
    assert not (ws / "projects" / "p1" / "alt.txt").exists()


def test_restore_ignores_archive_from_old_backup(ws, tmp_path) -> None:
    """Enthält ein altes Backup noch ein archive/, überschreibt es das Live-Archiv nicht."""
    from hydrahive.backup import restore
    (ws / "archive" / "agents" / "paket.tar.gz").write_bytes(b"live")
    src = tmp_path / "extract" / "workspaces"
    (src / "archive" / "agents").mkdir(parents=True)
    (src / "archive" / "agents" / "paket.tar.gz").write_bytes(b"alt")

    restore._atomic_replace_dir(src, ws)

    assert (ws / "archive" / "agents" / "paket.tar.gz").read_bytes() == b"live"


def test_restore_of_other_dirs_unchanged(tmp_path) -> None:
    from hydrahive.backup import restore
    src = tmp_path / "src"
    (src / "archive").mkdir(parents=True)
    (src / "archive" / "x").write_text("neu")
    dst = tmp_path / "agents"
    (dst / "archive").mkdir(parents=True)
    (dst / "archive" / "x").write_text("alt")

    restore._atomic_replace_dir(src, dst)

    assert (dst / "archive" / "x").read_text() == "neu"
