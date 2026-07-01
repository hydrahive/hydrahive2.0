"""System-Restore: config_dir (/etc/hydrahive2) liegt unter einem Elternpfad
(/etc), den der Service-User nicht beschreiben darf → Verzeichnis-rename schlägt
mit 'Permission denied' fehl.

Fix: _atomic_replace_dir erkennt nicht-schreibbares Elternverzeichnis und ersetzt
über _privileged_replace_dir (sudo -n bash, vorhandenes NOPASSWD-Recht). Der
data_dir-Pfad (schreibbares Elternverzeichnis) bleibt reiner Python-Move.
"""
from __future__ import annotations

import os

import pytest


def test_replace_writable_parent_uses_python_path(tmp_path, monkeypatch):
    """Schreibbares Elternverzeichnis → reiner Python-Move, KEIN sudo."""
    from hydrahive.backup import restore

    called = {"privileged": False}
    monkeypatch.setattr(
        restore, "_privileged_replace_dir",
        lambda s, d: called.__setitem__("privileged", True),
    )

    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("neu")
    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "file.txt").write_text("alt")

    restore._atomic_replace_dir(src, dst)

    assert called["privileged"] is False
    assert (dst / "file.txt").read_text() == "neu"


def test_replace_readonly_parent_uses_privileged_path(tmp_path, monkeypatch):
    """Nicht-schreibbares Elternverzeichnis → _privileged_replace_dir wird genutzt."""
    from hydrahive.backup import restore

    captured = {}
    monkeypatch.setattr(
        restore, "_privileged_replace_dir",
        lambda s, d: captured.update(src=s, dst=d),
    )
    # os.access für das Elternverzeichnis auf False zwingen (simuliert /etc)
    monkeypatch.setattr(restore.os, "access", lambda p, mode: False)

    src = tmp_path / "src"
    src.mkdir()
    dst = tmp_path / "etc-like" / "hydrahive2"

    restore._atomic_replace_dir(src, dst)

    assert captured["dst"] == dst
    assert captured["src"] == src


def test_privileged_replace_builds_sudo_command(tmp_path, monkeypatch):
    """_privileged_replace_dir ruft 'sudo -n bash -c <script>' mit dem
    korrekten mv/chown-Script (wenn nicht als root)."""
    from hydrahive.backup import restore

    recorded = {}

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, **kwargs):
        recorded["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(restore.subprocess, "run", fake_run)
    monkeypatch.setattr(restore.os, "getuid", lambda: 1000)  # nicht root
    monkeypatch.setattr(restore, "_service_user", lambda: "hydrahive")

    src = tmp_path / "src"
    dst = tmp_path / "target"
    restore._privileged_replace_dir(src, dst)

    cmd = recorded["cmd"]
    assert cmd[:3] == ["sudo", "-n", "bash"]
    assert cmd[3] == "-c"
    script = cmd[4]
    # Move + Auto-Rollback + Ownership-Wiederherstellung im Script
    assert str(dst) in script and str(src) in script
    assert ".old-restore" in script
    assert "chown -R" in script and "hydrahive:hydrahive" in script
    assert "chmod 770" in script


def test_privileged_replace_as_root_no_sudo(tmp_path, monkeypatch):
    """Läuft der Prozess bereits als root → bash ohne sudo-Präfix."""
    from hydrahive.backup import restore

    recorded = {}

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(restore.subprocess, "run",
                        lambda cmd, **k: recorded.update(cmd=cmd) or _Proc())
    monkeypatch.setattr(restore.os, "getuid", lambda: 0)  # root
    monkeypatch.setattr(restore, "_service_user", lambda: "hydrahive")

    restore._privileged_replace_dir(tmp_path / "s", tmp_path / "d")

    assert recorded["cmd"][0] == "bash"
    assert "sudo" not in recorded["cmd"]


def test_privileged_replace_raises_on_failure(tmp_path, monkeypatch):
    """Nicht-0-Exit des sudo-Scripts → RestoreError mit stderr."""
    from hydrahive.backup import restore
    from hydrahive.backup.validate import RestoreError

    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "mv: cannot move"

    monkeypatch.setattr(restore.subprocess, "run", lambda cmd, **k: _Proc())
    monkeypatch.setattr(restore.os, "getuid", lambda: 1000)
    monkeypatch.setattr(restore, "_service_user", lambda: "hydrahive")

    with pytest.raises(RestoreError, match="config_dir-Replace fehlgeschlagen"):
        restore._privileged_replace_dir(tmp_path / "s", tmp_path / "d")


def test_privileged_replace_real_move_as_root_only(tmp_path, monkeypatch):
    """Echter Move-Roundtrip OHNE sudo (getuid=0-Pfad, echtes bash) —
    verifiziert dass das Script mv + Auto-Rollback korrekt macht.
    Läuft nur wenn wir tatsächlich schreibende Rechte im tmp haben (immer)."""
    from hydrahive.backup import restore

    # Als 'root' behandeln → bash ohne sudo; chown/chmod auf tmp (eigene Files) ok
    monkeypatch.setattr(restore.os, "getuid", lambda: 0)
    monkeypatch.setattr(restore, "_service_user", lambda: __import__("getpass").getuser())

    src = tmp_path / "src"
    src.mkdir()
    (src / "neu.txt").write_text("N")
    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "alt.txt").write_text("A")

    restore._privileged_replace_dir(src, dst)

    assert (dst / "neu.txt").read_text() == "N"
    assert not (dst / "alt.txt").exists()          # altes Verzeichnis ersetzt
    assert not dst.with_suffix(dst.suffix + ".old-restore").exists()  # aufgeräumt
    assert not src.exists()                         # src wurde verschoben
