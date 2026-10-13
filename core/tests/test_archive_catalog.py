"""Archiv-Katalog und Papierkorb (Spec archiv-system.md, Etappe 1).

Der Katalog sind die .json-Dateien. Was jemand über die Samba-Freigabe
von Hand hineinlegt (ohne .json), erscheint als „manual“. Der Papierkorb
(.papierkorb, Samba recycle) wird nie gelistet und lässt sich nur
innerhalb des Archivs leeren.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from hydrahive.archive import catalog, package, trash
from hydrahive.settings import settings


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    r = tmp_path / "archiv"
    monkeypatch.setattr(settings, "archive_local_dir", r, raising=False)
    return r


def _pack(src: Path, kind: str = "agents", name: str = "a") -> dict:
    return package.pack(kind=kind, name=name, source_id="12345678", owner="till",
                        reason="agent_deleted", sources=[("ws", src)])


@pytest.fixture
def src(tmp_path) -> Path:
    s = tmp_path / "quelle"
    s.mkdir()
    (s / "a.txt").write_text("hallo")
    return s


def test_empty_or_missing_archive(root: Path) -> None:
    assert catalog.list_entries() == []
    u = catalog.usage()
    assert u["exists"] is False and u["count"] == 0 and u["trash_bytes"] == 0


def test_lists_packed_entries_newest_first(root: Path, src: Path) -> None:
    a = _pack(src, "agents", "erster")
    b = _pack(src, "projects", "zweiter")
    os.utime(root / "agents" / (a["file"] + ".json"), (1, 1))

    entries = catalog.list_entries()

    assert [e["file"] for e in entries] == [b["file"], a["file"]]
    assert entries[0]["kind"] == "projects" and entries[0]["manual"] is False
    assert entries[0]["sha256"] == b["sha256"]


def test_filter_by_kind(root: Path, src: Path) -> None:
    _pack(src, "agents")
    _pack(src, "projects")

    assert {e["kind"] for e in catalog.list_entries(kind="agents")} == {"agents"}
    with pytest.raises(ValueError):
        catalog.list_entries(kind="../etc")


def test_hand_placed_files_are_manual(root: Path, src: Path) -> None:
    """Über Samba abgelegt: keine .json → manual, mit Größe und Pfad relativ zum Archiv."""
    _pack(src)
    (root / "uploads").mkdir(parents=True)
    (root / "uploads" / "alte-platte.zip").write_bytes(b"x" * 10)
    (root / "eigener-ordner").mkdir()
    (root / "eigener-ordner" / "notiz.txt").write_text("n")

    manual = [e for e in catalog.list_entries() if e["manual"]]

    paths = {e["path"] for e in manual}
    assert paths == {"uploads/alte-platte.zip", "eigener-ordner/notiz.txt"}
    by_path = {e["path"]: e for e in manual}
    assert by_path["uploads/alte-platte.zip"]["size"] == 10
    assert by_path["uploads/alte-platte.zip"]["kind"] == "uploads"
    assert by_path["eigener-ordner/notiz.txt"]["kind"] is None


def test_trash_part_files_and_json_never_listed_as_manual(root: Path, src: Path) -> None:
    _pack(src)
    (root / ".papierkorb" / "agents").mkdir(parents=True)
    (root / ".papierkorb" / "agents" / "weg.tar.gz").write_bytes(b"y" * 7)
    (root / "agents" / "halb.tar.gz.part").write_bytes(b"z")

    entries = catalog.list_entries()

    assert len(entries) == 1 and entries[0]["manual"] is False
    assert catalog.usage()["trash_bytes"] == 7


def test_broken_json_does_not_break_the_list(root: Path, src: Path) -> None:
    good = _pack(src)
    (root / "agents" / "kaputt.tar.gz").write_bytes(b"k")
    (root / "agents" / "kaputt.tar.gz.json").write_text("{ nicht json")

    entries = catalog.list_entries()

    assert good["file"] in {e["file"] for e in entries if not e["manual"]}
    assert any(e["path"] == "agents/kaputt.tar.gz" and e["manual"] for e in entries)


def test_usage_counts(root: Path, src: Path) -> None:
    _pack(src, "agents")
    _pack(src, "agents")
    _pack(src, "projects")

    u = catalog.usage()

    assert u["exists"] is True and u["writable"] is True
    assert u["count"] == 3 and u["by_kind"] == {"agents": 2, "projects": 1}
    assert u["used_bytes"] > 0 and u["free_bytes"] > 0


def test_empty_trash_removes_only_inside(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "draussen"
    outside.mkdir()
    (outside / "wichtig.txt").write_text("bleibt")
    t = root / ".papierkorb"
    (t / "agents").mkdir(parents=True)
    (t / "agents" / "alt.tar.gz").write_bytes(b"a")
    (t / "link-nach-draussen").symlink_to(outside)
    (root / "agents").mkdir()
    (root / "agents" / "bleibt.tar.gz").write_bytes(b"b")

    freed = trash.empty_trash()

    assert freed >= 1
    assert t.is_dir() and list(t.iterdir()) == []
    assert (outside / "wichtig.txt").read_text() == "bleibt"
    assert (root / "agents" / "bleibt.tar.gz").exists()


def test_empty_trash_refuses_symlinked_trash(root: Path, tmp_path: Path) -> None:
    """Ist .papierkorb selbst ein Symlink nach draußen, wird nichts gelöscht."""
    outside = tmp_path / "draussen"
    outside.mkdir()
    (outside / "wichtig.txt").write_text("bleibt")
    root.mkdir()
    (root / ".papierkorb").symlink_to(outside)

    with pytest.raises(ValueError):
        trash.empty_trash()
    assert (outside / "wichtig.txt").exists()
