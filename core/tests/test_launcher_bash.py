"""shell_exec läuft in bash, nicht in dash (/bin/sh).

LLMs generieren ständig Bashisms (`[[ ]]`, Prozesssubstitution `<(...)`, `&>`).
In dash failen die mit kryptischen Syntaxfehlern → Agent stolpert. Der echte
DevLauncher muss sie ausführen können.
"""
from __future__ import annotations

import asyncio
import shutil

import pytest

from hydrahive.tools._launcher import DevLauncher

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash nicht verfügbar")


def _run(cmd: str, tmp):
    return asyncio.run(DevLauncher().run(cmd, cwd=tmp))


def test_double_bracket_test_is_bash(tmp_path):
    res = _run("[[ foo == foo ]] && echo match", tmp_path)
    assert res.exit_code == 0, res.stderr
    assert "match" in res.stdout


def test_process_substitution_is_bash(tmp_path):
    res = _run("cat <(echo hallo)", tmp_path)
    assert res.exit_code == 0, res.stderr
    assert "hallo" in res.stdout


def test_plain_command_still_works(tmp_path):
    res = _run("echo hi", tmp_path)
    assert res.exit_code == 0
    assert "hi" in res.stdout
