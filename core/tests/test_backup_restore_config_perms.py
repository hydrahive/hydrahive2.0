"""System-Restore: config_dir (/etc/hydrahive2) kann NICHT per Verzeichnis-rename
ersetzt werden — zwei Gründe, die zusammen auftreten:

1. /etc gehört root → Service-User (hydrahive) darf dort nicht umbenennen (EPERM).
2. Die systemd-Unit setzt ReadWritePaths=/etc/hydrahive2 → das Verzeichnis ist im
   Service-Namespace ein Bind-Mount → rename() gibt EBUSY.

Fix: _atomic_replace_dir testet ob dst umbenennbar ist (_can_rename_dir). Wenn
nicht, wird der INHALT in-place ersetzt (_replace_dir_contents) — Mount-Point-
und Permission-sicher, ohne sudo. Fremd-owned Einträge (root:hydrahive env/
extensions) werden übersprungen (hostspezifisch).
"""
from __future__ import annotations

import pytest


def test_can_rename_normal_dir(tmp_path):
    """Normales Verzeichnis mit schreibbarem Parent → umbenennbar."""
    from hydrahive.backup import restore

    dst = tmp_path / "d"
    dst.mkdir()
    (dst / "x").write_text("1")
    assert restore._can_rename_dir(dst, tmp_path / "d.old") is True
    # nach dem Probe-Test steht dst wieder am Platz, Inhalt intakt
    assert (dst / "x").read_text() == "1"


def test_can_rename_readonly_parent(tmp_path, monkeypatch):
    """Nicht-schreibbares Elternverzeichnis (simuliert /etc) → nicht umbenennbar."""
    from hydrahive.backup import restore

    dst = tmp_path / "d"
    dst.mkdir()
    monkeypatch.setattr(restore.os, "access", lambda p, mode: False)
    assert restore._can_rename_dir(dst, tmp_path / "d.old") is False


def test_replace_dir_uses_rename_when_possible(tmp_path, monkeypatch):
    """Umbenennbares Ziel → schneller rename-Pfad, KEIN Content-Replace."""
    from hydrahive.backup import restore

    called = {"contents": False}
    monkeypatch.setattr(restore, "_replace_dir_contents",
                        lambda s, d: called.__setitem__("contents", True))

    src = tmp_path / "src"; src.mkdir(); (src / "neu").write_text("N")
    dst = tmp_path / "dst"; dst.mkdir(); (dst / "alt").write_text("A")

    restore._atomic_replace_dir(src, dst)
    assert called["contents"] is False
    assert (dst / "neu").read_text() == "N"
    assert not (dst / "alt").exists()


def test_replace_dir_falls_back_to_contents(tmp_path, monkeypatch):
    """Nicht umbenennbares Ziel → Content-Replace-Pfad."""
    from hydrahive.backup import restore

    captured = {}
    monkeypatch.setattr(restore, "_can_rename_dir", lambda d, p: False)
    monkeypatch.setattr(restore, "_replace_dir_contents",
                        lambda s, d: captured.update(src=s, dst=d))

    src = tmp_path / "src"; src.mkdir()
    dst = tmp_path / "dst"; dst.mkdir()
    restore._atomic_replace_dir(src, dst)
    assert captured == {"src": src, "dst": dst}


# ---------------------------------------------------------------- Content-Replace
def test_replace_contents_swaps_files(tmp_path):
    """In-place Content-Replace: dst behält seine Identität (Mount-Point-sicher),
    Inhalt wird ausgetauscht, .old-restore aufgeräumt."""
    from hydrahive.backup import restore

    src = tmp_path / "src"; src.mkdir()
    (src / "llm.json").write_text("neu")
    (src / "sub").mkdir(); (src / "sub" / "a.txt").write_text("x")

    dst = tmp_path / "dst"; dst.mkdir()
    dst_inode = dst.stat().st_ino
    (dst / "llm.json").write_text("alt")
    (dst / "weg.json").write_text("weg")

    restore._replace_dir_contents(src, dst)

    assert dst.stat().st_ino == dst_inode          # dst NICHT bewegt (Mount-safe)
    assert (dst / "llm.json").read_text() == "neu"  # ersetzt
    assert (dst / "sub" / "a.txt").read_text() == "x"  # neu rein
    assert not (dst / "weg.json").exists()          # alter Inhalt weg
    assert not (dst / ".old-restore").exists()       # Backup aufgeräumt


def test_replace_contents_skips_unmovable(tmp_path, monkeypatch):
    """Fremd-owned Einträge (können nicht umbenannt werden) werden übersprungen
    und bleiben unverändert erhalten — env/extensions bleiben vom Zielserver."""
    from hydrahive.backup import restore

    src = tmp_path / "src"; src.mkdir()
    (src / "llm.json").write_text("neu")
    (src / "env").write_text("SRC-ENV")  # käme aus Backup, soll NICHT übernommen werden

    dst = tmp_path / "dst"; dst.mkdir()
    (dst / "llm.json").write_text("alt")
    (dst / "env").write_text("HOST-ENV")  # hostspezifisch, "fremd-owned"

    real_rename = restore.Path.rename

    def guarded_rename(self, target):
        # 'env' simuliert fremd-owned: rename ins Backup schlägt fehl
        if self.name == "env" and ".old-restore" in str(target):
            raise OSError("Operation not permitted")
        return real_rename(self, target)

    monkeypatch.setattr(restore.Path, "rename", guarded_rename)

    restore._replace_dir_contents(src, dst)

    assert (dst / "llm.json").read_text() == "neu"     # normal ersetzt
    assert (dst / "env").read_text() == "HOST-ENV"      # übersprungen, Host-Wert bleibt


def test_replace_contents_rollback_on_error(tmp_path, monkeypatch):
    """Fehler beim Einbringen des neuen Inhalts → alter Inhalt wird zurückgeholt."""
    from hydrahive.backup import restore

    src = tmp_path / "src"; src.mkdir()
    (src / "a.json").write_text("A-neu")
    (src / "b.json").write_text("B-neu")

    dst = tmp_path / "dst"; dst.mkdir()
    (dst / "a.json").write_text("A-alt")
    (dst / "b.json").write_text("B-alt")

    real_move = restore.shutil.move
    state = {"n": 0}

    def flaky_move(s, d):
        state["n"] += 1
        if state["n"] == 2:  # zweites Einbringen schlägt fehl
            raise OSError("disk full")
        return real_move(s, d)

    monkeypatch.setattr(restore.shutil, "move", flaky_move)

    with pytest.raises(OSError):
        restore._replace_dir_contents(src, dst)

    # Rollback: beide Originale wieder da, kein .old-restore-Rest
    assert (dst / "a.json").read_text() == "A-alt"
    assert (dst / "b.json").read_text() == "B-alt"
    assert not (dst / ".old-restore").exists()


def test_replace_dir_new_target_just_moves(tmp_path):
    """Ziel existiert noch nicht → einfacher move."""
    from hydrahive.backup import restore

    src = tmp_path / "src"; src.mkdir(); (src / "x").write_text("1")
    dst = tmp_path / "neu-dst"
    restore._atomic_replace_dir(src, dst)
    assert (dst / "x").read_text() == "1"


# ---------------------------------------------------------------- _replace_file (DB)
def test_replace_file_same_device_rename(tmp_path):
    """src+dst gleiches Filesystem → rename-Pfad, Datei ersetzt."""
    from hydrahive.backup import restore

    src = tmp_path / "new.db"; src.write_text("NEU")
    dst = tmp_path / "sessions.db"; dst.write_text("ALT")
    restore._replace_file(src, dst)
    assert dst.read_text() == "NEU"
    assert not src.exists()


def test_replace_file_cross_device_falls_back_to_copy(tmp_path, monkeypatch):
    """EXDEV bei rename → copy-Fallback (in temp neben dst, dann atomarer rename)."""
    import errno
    from hydrahive.backup import restore

    src = tmp_path / "new.db"; src.write_text("NEU")
    dst = tmp_path / "sessions.db"; dst.write_text("ALT")

    calls = {"n": 0}
    real_replace = restore.Path.replace

    def flaky_replace(self, target):
        # Erster replace-Aufruf (src->dst) simuliert cross-device; der zweite
        # (tmp->dst, innerhalb Ziel-FS) läuft echt durch.
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return real_replace(self, target)

    monkeypatch.setattr(restore.Path, "replace", flaky_replace)

    restore._replace_file(src, dst)
    assert dst.read_text() == "NEU"
    assert not src.exists()
    assert not dst.with_name(dst.name + ".restore-tmp").exists()


def test_replace_file_other_oserror_propagates(tmp_path, monkeypatch):
    """Ein anderer OSError als EXDEV wird NICHT geschluckt."""
    import errno
    from hydrahive.backup import restore

    src = tmp_path / "new.db"; src.write_text("NEU")
    dst = tmp_path / "sessions.db"

    def fail(self, target):
        raise OSError(errno.EACCES, "Permission denied")
    monkeypatch.setattr(restore.Path, "replace", fail)

    with pytest.raises(OSError):
        restore._replace_file(src, dst)
