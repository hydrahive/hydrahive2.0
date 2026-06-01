"""System-Restore darf keine bösartigen Symlinks ins Live-System pflanzen
(Issue #182).

filter="tar" erlaubt einen Symlink mit absolutem/eskapierendem Ziel INNERHALB
des Zielordners; nach _atomic_replace_dir landet er dauerhaft im Live-Config-
Verzeichnis. filter="data" lehnt das mit AbsoluteLinkError ab.
"""
from __future__ import annotations

import io
import json
import tarfile

import pytest


def _build_malicious_archive(path, *, link_target: str) -> None:
    with tarfile.open(path, "w:gz") as tar:
        # gültiges Manifest, damit validate_archive durchläuft
        manifest = json.dumps({"version": "1", "kind": "system"}).encode()
        mi = tarfile.TarInfo("manifest.json")
        mi.size = len(manifest)
        tar.addfile(mi, io.BytesIO(manifest))
        # bösartiger Symlink innerhalb von config/
        link = tarfile.TarInfo("config/evil")
        link.type = tarfile.SYMTYPE
        link.linkname = link_target
        tar.addfile(link)


@pytest.mark.parametrize("target", ["/etc/passwd", "../../../../etc/passwd"])
def test_restore_rejects_malicious_symlink(client, monkeypatch, tmp_path, target):
    from hydrahive.backup import restore
    from hydrahive.settings import settings

    # Rollback-Backup-Schritt ausklammern — Test fokussiert die Extraktion.
    monkeypatch.setattr(restore, "_create_rollback_backup", lambda: tmp_path / "rb.tar.gz")
    monkeypatch.setattr(restore, "_trigger_restart", lambda: None)

    archive = tmp_path / "evil.tar.gz"
    _build_malicious_archive(archive, link_target=target)

    with pytest.raises(tarfile.TarError):
        restore.restore_system_archive(archive)

    # Kein Symlink darf im Live-Config-Verzeichnis gelandet sein.
    assert not (settings.config_dir / "evil").exists()
    assert not (settings.config_dir / "evil").is_symlink()
