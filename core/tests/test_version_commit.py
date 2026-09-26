"""Footer-Hash und Update-Status bleiben für jeden Clone deterministisch."""
from __future__ import annotations

from pathlib import Path

from hydrahive.api import version


class _Result:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode


def test_commit_ist_deterministisch_8_zeichen(monkeypatch):
    full = "874dedd0" + "a" * 32  # voller 40-Zeichen-Hash

    captured: dict = {}

    class FakeResult:
        stdout = full + "\n"

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeResult()

    monkeypatch.setattr(version.subprocess, "run", fake_run)

    commit = version._detect_git_commit()

    assert commit == "874dedd0"               # exakt 8, nie verkürzt
    assert "--short" not in captured["cmd"]   # voller Hash holen, nicht git-adaptiv


def test_commit_none_ohne_git(monkeypatch):
    monkeypatch.setattr(version, "_REPO_ROOT", version.Path("/nonexistent/repo"))
    assert version._detect_git_commit() is None


def test_update_behind_lokal_voraus_ist_keine_verfuegbare_aktualisierung(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(version, "_REPO_ROOT", Path(tmp_path))
    monkeypatch.setattr(version, "_remote_url_https", lambda: "https://example.test/repo.git")

    def fake_run(cmd, **_kw):
        if cmd[1] == "ls-remote":
            return _Result("remote123\n")
        if cmd[-2:] == ["rev-parse", "HEAD"]:
            return _Result("local456\n")
        if cmd[-3:] == ["--is-ancestor", "remote123", "local456"]:
            return _Result(returncode=0)
        raise AssertionError(cmd)

    monkeypatch.setattr(version.subprocess, "run", fake_run)

    assert version._check_update_behind() == 0


def test_update_behind_remote_neuer_oder_divergiert(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(version, "_REPO_ROOT", Path(tmp_path))
    monkeypatch.setattr(version, "_remote_url_https", lambda: "https://example.test/repo.git")

    def fake_run(cmd, **_kw):
        if cmd[1] == "ls-remote":
            return _Result("remote123\n")
        if cmd[-2:] == ["rev-parse", "HEAD"]:
            return _Result("local456\n")
        if cmd[-3:] == ["--is-ancestor", "remote123", "local456"]:
            return _Result(returncode=1)
        raise AssertionError(cmd)

    monkeypatch.setattr(version.subprocess, "run", fake_run)

    assert version._check_update_behind() == 1
