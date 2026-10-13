"""Etappe 1b: Archiv umziehen (Spec archiv-system.md, „Umzug im Hintergrund“).

Nie Daten verlieren: erst kopieren und prüfen, dann umstellen, dann nur geprüft kopierte Dateien am alten Ort löschen.
Fehler vor dem Umstellen → alles wie vorher. Neustart mittendrin → zurückrollen bzw. Aufräumen fortsetzen.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydrahive.archive import location, move, package, setup
from hydrahive.settings import settings


@pytest.fixture
def env(tmp_path, monkeypatch) -> dict:
    ws, cfg = tmp_path / "workspaces", tmp_path / "config"
    ws.mkdir()
    cfg.mkdir()
    monkeypatch.setattr(settings, "workspaces_dir", ws, raising=False)
    monkeypatch.setattr(settings, "config_dir", cfg, raising=False)
    monkeypatch.setattr(settings, "samba_includes_dir", tmp_path / "kein-samba", raising=False)
    setup.ensure_archive()
    src = tmp_path / "quelle"
    src.mkdir()
    (src / "a.txt").write_text("inhalt" * 100)
    meta = package.pack(kind="agents", name="Alt", source_id="11111111", owner="till", reason="agent_deleted",
                        sources=[("ws", src)])
    old = location.archive_root()
    (old / "uploads" / "hand.zip").write_bytes(b"von hand")
    (old / ".papierkorb" / "uploads").mkdir(parents=True)
    (old / ".papierkorb" / "uploads" / "weg.txt").write_text("papierkorb")
    return {"old": old, "new": tmp_path / "platte" / "hydrahive-archiv", "cfg": cfg, "meta": meta}


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_check_target(env, tmp_path) -> None:
    assert move.check_target(env["new"]) == []
    (env["new"]).mkdir(parents=True)
    (env["new"] / "fremd.txt").write_text("x")
    assert "target_not_empty" in move.check_target(env["new"])
    assert "target_inside_current" in move.check_target(env["old"] / "uploads" / "x")
    assert "current_inside_target" in move.check_target(env["old"].parent)
    assert "same_location" in move.check_target(env["old"])


def test_check_target_needs_space(env, monkeypatch) -> None:
    monkeypatch.setattr(move, "_free_bytes", lambda p: 10)
    assert "not_enough_space" in move.check_target(env["new"])


def test_state_remembers_empty_target(env, monkeypatch) -> None:
    """run_move schreibt den Merker, auf den sich recover() verlässt."""
    seen = {}
    real = move._write_state
    monkeypatch.setattr(move, "_write_state", lambda d: (seen.update(d), real(d)))
    move.run_move(env["new"])
    assert seen["target_was_empty"] is True


def test_move_copies_verifies_switches_and_cleans(env) -> None:
    before = _files(env["old"])
    result = move.run_move(env["new"])
    assert result["state"] == "done"
    assert location.archive_root() == env["new"]
    assert _files(env["new"]) == before, "alles inklusive Papierkorb und Handablage 1:1 drüben"
    assert _files(env["old"]) == {}, "alter Ort leer"
    assert json.loads((env["cfg"] / "archive.json").read_text())["local_dir"] == str(env["new"])
    assert not (env["cfg"] / "archive-move.json").exists()


def test_progress_is_reported(env) -> None:
    seen = []
    move.run_move(env["new"], on_progress=lambda s: seen.append(dict(s)))
    assert seen[0]["state"] == "copying" and seen[0]["total_bytes"] > 0
    assert any(s["state"] == "verifying" for s in seen)
    assert seen[-1]["copied_bytes"] == seen[-1]["total_bytes"]


def test_checksum_mismatch_rolls_back(env, monkeypatch) -> None:
    real = move._copy_file

    def broken(src: Path, dst: Path) -> None:
        real(src, dst)
        if dst.name.endswith(".tar.gz"):
            dst.write_bytes(b"kaputt")
    monkeypatch.setattr(move, "_copy_file", broken)
    before = _files(env["old"])

    result = move.run_move(env["new"])

    assert result["state"] == "failed" and result["error"] == "verify_failed"
    assert location.archive_root() == env["old"]
    assert _files(env["old"]) == before
    assert not env["new"].exists() or _files(env["new"]) == {}


def test_copy_error_rolls_back(env, monkeypatch) -> None:
    def boom(src, dst):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(move, "_copy_file", boom)
    result = move.run_move(env["new"])
    assert result["state"] == "failed" and "No space" in result["detail"]
    assert location.archive_root() == env["old"]


def test_files_added_during_move_stay_and_are_reported(env, monkeypatch) -> None:
    """Etwas, das am alten Ort nach dem Kopieren auftaucht, wird nie gelöscht."""
    real = move._verify

    def verify_then_add(*a, **k):
        ok = real(*a, **k)
        (env["old"] / "uploads" / "spaet.txt").write_text("spät")
        return ok
    monkeypatch.setattr(move, "_verify", verify_then_add)
    result = move.run_move(env["new"])
    assert result["state"] == "done"
    assert (env["old"] / "uploads" / "spaet.txt").read_text() == "spät"
    assert result["left_behind"] == ["uploads/spaet.txt"]


def test_restart_before_switch_rolls_back(env) -> None:
    env["new"].mkdir(parents=True)
    (env["new"] / "agents").mkdir()
    (env["new"] / "agents" / "halb.tar.gz").write_bytes(b"halb")
    (env["cfg"] / "archive-move.json").write_text(json.dumps(
        {"state": "copying", "source": str(env["old"]), "target": str(env["new"]), "copied": ["agents/halb.tar.gz"]}))
    move.recover()
    assert location.archive_root() == env["old"]
    assert not (env["new"] / "agents" / "halb.tar.gz").exists()
    assert not (env["cfg"] / "archive-move.json").exists()


def test_restart_before_switch_removes_files_not_yet_in_state(env) -> None:
    """Fund auf hydratest (13.10.): Der Zustand wird nicht nach jeder Datei geschrieben. Nach hartem Abbruch lagen am
    Ziel Dateien, die nicht in „copied“ standen – darunter eine halb kopierte. Das Ziel war vorher leer
    (check_target), also gehört dort alles dem Umzug und muss weg."""
    env["new"].mkdir(parents=True)
    (env["new"] / "projects").mkdir()
    (env["new"] / "projects" / "halb.tar.gz").write_bytes(b"halb")
    (env["new"] / "agents").mkdir()
    (env["new"] / "agents" / "fertig.tar.gz").write_bytes(b"fertig")
    (env["cfg"] / "archive-move.json").write_text(json.dumps(
        {"state": "copying", "source": str(env["old"]), "target": str(env["new"]), "copied": [],
         "target_was_empty": True}))
    move.recover()
    assert not env["new"].exists() or _files(env["new"]) == {}
    assert location.archive_root() == env["old"]


def test_recover_never_touches_a_target_that_was_not_empty(env) -> None:
    """Ohne Merker „Ziel war leer“ (alte Zustandsdatei) wird nur Bekanntes entfernt."""
    env["new"].mkdir(parents=True)
    (env["new"] / "fremd.txt").write_text("gehört nicht dem Umzug")
    (env["cfg"] / "archive-move.json").write_text(json.dumps(
        {"state": "copying", "source": str(env["old"]), "target": str(env["new"]), "copied": [],
         "target_was_empty": False}))
    move.recover()
    assert (env["new"] / "fremd.txt").read_text() == "gehört nicht dem Umzug"


def test_restart_after_switch_finishes_cleanup(env) -> None:
    before = _files(env["old"])
    for rel, data in before.items():
        (env["new"] / rel).parent.mkdir(parents=True, exist_ok=True)
        (env["new"] / rel).write_bytes(data)
    (env["cfg"] / "archive.json").write_text(json.dumps({"local_dir": str(env["new"])}))
    (env["cfg"] / "archive-move.json").write_text(json.dumps(
        {"state": "cleanup", "source": str(env["old"]), "target": str(env["new"]), "copied": sorted(before)}))
    move.recover()
    assert location.archive_root() == env["new"]
    assert _files(env["old"]) == {}
    assert _files(env["new"]) == before


def test_pack_refused_while_moving(env) -> None:
    (env["cfg"] / "archive-move.json").write_text(json.dumps({"state": "copying", "source": "a", "target": "b"}))
    with pytest.raises(package.ArchiveBusy):
        package.pack(kind="agents", name="x", source_id="22222222", owner=None, reason="t", sources=[])


def test_only_one_move_at_a_time(env) -> None:
    (env["cfg"] / "archive-move.json").write_text(json.dumps({"state": "copying", "source": "a", "target": "b"}))
    assert "move_running" in move.check_target(env["new"])
