"""Archiv-Ort und Einrichtung ohne Installer (Spec archiv-system.md, „Ort und Einrichtung“).

Till, 13.10.: Es gibt viele Installationen, die wir nicht kennen. Kein install.conf, keine Shell –
HydraHive legt Ordner und Samba-Freigabe selbst an, der Ort liegt bei den Projektdaten.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from hydrahive.archive import location, setup
from hydrahive.settings import settings


@pytest.fixture
def env(tmp_path, monkeypatch) -> dict:
    ws = tmp_path / "workspaces"
    cfg = tmp_path / "config"
    inc = tmp_path / "hh-projects.d"
    ws.mkdir()
    cfg.mkdir()
    monkeypatch.setattr(settings, "workspaces_dir", ws, raising=False)
    monkeypatch.setattr(settings, "config_dir", cfg, raising=False)
    monkeypatch.setattr(settings, "samba_includes_dir", inc, raising=False)
    return {"ws": ws, "cfg": cfg, "inc": inc}


def test_default_location_is_next_to_project_data(env) -> None:
    """Standard liegt auf derselben Platte wie die Projekte (Prod: workspaces auf 16 TB)."""
    assert location.archive_root() == env["ws"] / "archive"


def test_archive_json_wins(env, tmp_path) -> None:
    other = tmp_path / "grosse-platte" / "archiv"
    (env["cfg"] / "archive.json").write_text(json.dumps({"local_dir": str(other)}))
    assert location.archive_root() == other


@pytest.mark.parametrize("content", ["{kaputt", '{"local_dir": "relativ/pfad"}', '{"local_dir": 5}', "[]"])
def test_broken_or_unsafe_config_falls_back_to_default(env, content) -> None:
    (env["cfg"] / "archive.json").write_text(content)
    assert location.archive_root() == env["ws"] / "archive"


def test_no_env_variable_anymore(env, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HH_ARCHIVE_LOCAL_DIR", str(tmp_path / "env-ort"))
    assert location.archive_root() == env["ws"] / "archive"


def test_share_wanted_default_on_and_switchable(env) -> None:
    assert location.share_wanted() is True
    location.set_share_wanted(False)
    assert location.share_wanted() is False
    data = json.loads((env["cfg"] / "archive.json").read_text())
    assert data == {"share": False}
    location.set_share_wanted(True)
    assert location.share_wanted() is True


def test_set_share_keeps_local_dir(env, tmp_path) -> None:
    other = str(tmp_path / "x" / "archiv")
    (env["cfg"] / "archive.json").write_text(json.dumps({"local_dir": other}))
    location.set_share_wanted(False)
    assert json.loads((env["cfg"] / "archive.json").read_text()) == {"local_dir": other, "share": False}


def test_ensure_without_samba_creates_only_folders(env) -> None:
    result = setup.ensure_archive()
    root = env["ws"] / "archive"
    assert {p.name for p in root.iterdir()} == {"agents", "projects", "users", "backups", "uploads", ".papierkorb"}
    assert stat.S_IMODE(root.stat().st_mode) & 0o2775 == 0o2775
    assert result == {"folder": True, "share": "no_samba"}
    assert not env["inc"].exists()


def test_ensure_with_samba_writes_share_and_index(env) -> None:
    env["inc"].mkdir()
    (env["inc"] / "0190-proj.conf").write_text("[Projekt]\n")
    result = setup.ensure_archive()
    conf = (env["inc"] / "_system-archiv.conf").read_text()
    assert f"path = {env['ws'] / 'archive'}" in conf
    assert "[HydraHive_Archiv]" in conf and "read only = no" in conf
    assert "vfs objects = recycle" in conf and "recycle:repository = .papierkorb" in conf
    assert f"valid users = {settings.samba_user}" in conf
    index = (env["inc"] / "_index.conf").read_text().splitlines()
    assert f"include = {env['inc'] / '_system-archiv.conf'}" in index
    assert f"include = {env['inc'] / '0190-proj.conf'}" in index, "Projekt-Freigaben müssen bleiben"
    assert result == {"folder": True, "share": "on"}


def test_ensure_is_idempotent_and_does_not_rewrite(env) -> None:
    env["inc"].mkdir()
    setup.ensure_archive()
    conf = env["inc"] / "_system-archiv.conf"
    os.utime(conf, (1, 1))
    setup.ensure_archive()
    assert conf.stat().st_mtime == 1, "unveränderte Freigabe wird nicht neu geschrieben"


def test_share_follows_location(env, tmp_path) -> None:
    env["inc"].mkdir()
    setup.ensure_archive()
    other = tmp_path / "andere-platte" / "archiv"
    (env["cfg"] / "archive.json").write_text(json.dumps({"local_dir": str(other)}))
    setup.ensure_archive()
    assert f"path = {other}" in (env["inc"] / "_system-archiv.conf").read_text()
    assert (other / "agents").is_dir()


def test_switch_off_removes_share_but_keeps_data(env) -> None:
    env["inc"].mkdir()
    setup.ensure_archive()
    (env["ws"] / "archive" / "uploads" / "datei.txt").write_text("bleibt")
    location.set_share_wanted(False)
    result = setup.ensure_archive()
    assert not (env["inc"] / "_system-archiv.conf").exists()
    assert "_system-archiv" not in (env["inc"] / "_index.conf").read_text()
    assert (env["ws"] / "archive" / "uploads" / "datei.txt").read_text() == "bleibt"
    assert result["share"] == "off"


def test_index_stays_group_writable_for_project_shares(env) -> None:
    """Fund 13.10.: Der alte Installer-Weg hinterließ _index.conf als 0644 – danach konnte das
    Backend keine Projekt-Freigabe mehr schalten. Die Einrichtung darf das nie verschlechtern."""
    env["inc"].mkdir()
    setup.ensure_archive()
    mode = stat.S_IMODE((env["inc"] / "_index.conf").stat().st_mode)
    assert mode & 0o060 == 0o060


def test_ensure_never_raises(env, monkeypatch) -> None:
    """Der Start des Dienstes darf an der Einrichtung nie scheitern."""
    env["inc"].mkdir()
    def boom(*_a, **_k):
        raise PermissionError("kein Recht")
    monkeypatch.setattr(Path, "mkdir", boom)
    result = setup.ensure_archive()
    assert result["folder"] is False and result["error"]
