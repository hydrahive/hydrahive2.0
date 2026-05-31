"""Footer-Hash deterministisch: feste 8 Zeichen, unabhängig davon wie git auf
dem jeweiligen Clone abkürzt (`--short` variiert je nach Objekt-Anzahl → auf
dem Server fehlte eine Stelle gegenüber dem 8-stelligen Hash anderswo)."""
from __future__ import annotations

from hydrahive.api import version


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
