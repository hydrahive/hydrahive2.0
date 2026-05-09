"""Tests für safe_path + file_read + file_write + file_patch.

safe_path wird einzeln geprüft (Path-Traversal-Schutz, Symlinks).
Die drei Tools werden über _execute() durchgesteuert mit echten
Files in tmp_path — keine Subprocess-Aufrufe nötig.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.tools import file_patch, file_read, file_write
from hydrahive.tools._path import PathOutsideWorkspace, safe_path
from hydrahive.tools.base import ToolContext


def _ctx(workspace: Path) -> ToolContext:
    return ToolContext(session_id="s", agent_id="", user_id="u", workspace=workspace)


def _run(coro):
    return asyncio.run(coro)


# --- safe_path -----------------------------------------------------------

def test_safe_path_relativer_pfad_resolved_unter_workspace(tmp_path):
    p = safe_path(tmp_path, "sub/file.txt")
    assert p == (tmp_path / "sub" / "file.txt").resolve()


def test_safe_path_absoluter_pfad_innerhalb_ok(tmp_path):
    target = tmp_path / "x.txt"
    p = safe_path(tmp_path, str(target))
    assert p == target.resolve()


def test_safe_path_absoluter_pfad_ausserhalb_blockiert(tmp_path):
    with pytest.raises(PathOutsideWorkspace):
        safe_path(tmp_path, "/etc/passwd")


def test_safe_path_dotdot_traversal_blockiert(tmp_path):
    with pytest.raises(PathOutsideWorkspace):
        safe_path(tmp_path, "../../etc/passwd")


def test_safe_path_workspace_selbst_ok(tmp_path):
    assert safe_path(tmp_path, str(tmp_path)) == tmp_path.resolve()


def test_safe_path_leerer_string_blockiert(tmp_path):
    with pytest.raises(PathOutsideWorkspace):
        safe_path(tmp_path, "")


def test_safe_path_symlink_aus_workspace_raus_blockiert(tmp_path):
    outside = tmp_path.parent / "outside_target"
    outside.write_text("secret")
    link = tmp_path / "link"
    link.symlink_to(outside)
    try:
        with pytest.raises(PathOutsideWorkspace):
            safe_path(tmp_path, "link")
    finally:
        outside.unlink(missing_ok=True)


# --- file_read -----------------------------------------------------------

def test_file_read_nicht_existierende_datei(tmp_path):
    res = _run(file_read._execute({"path": "missing.txt"}, _ctx(tmp_path)))
    assert not res.success
    assert "nicht gefunden" in res.error


def test_file_read_pfad_ausserhalb_workspace(tmp_path):
    res = _run(file_read._execute({"path": "/etc/passwd"}, _ctx(tmp_path)))
    assert not res.success
    assert "außerhalb" in res.error.lower() or "outside" in res.error.lower()


def test_file_read_verzeichnis_statt_datei(tmp_path):
    (tmp_path / "subdir").mkdir()
    res = _run(file_read._execute({"path": "subdir"}, _ctx(tmp_path)))
    assert not res.success


def test_file_read_happy_path_mit_zeilennummern(tmp_path):
    (tmp_path / "x.txt").write_text("a\nb\nc\n")
    res = _run(file_read._execute({"path": "x.txt"}, _ctx(tmp_path)))
    assert res.success
    assert "     1\ta" in res.output
    assert "     2\tb" in res.output
    assert "     3\tc" in res.output


def test_file_read_offset_und_limit(tmp_path):
    (tmp_path / "x.txt").write_text("\n".join(str(i) for i in range(1, 11)))
    res = _run(file_read._execute({"path": "x.txt", "offset": 5, "limit": 3}, _ctx(tmp_path)))
    assert res.success
    assert "     5\t5" in res.output
    assert "     7\t7" in res.output
    assert "8" not in res.output.split("\n")[-1]


def test_file_read_truncated_flag_wenn_mehr_zeilen(tmp_path):
    (tmp_path / "x.txt").write_text("\n".join(str(i) for i in range(100)))
    res = _run(file_read._execute({"path": "x.txt", "limit": 10}, _ctx(tmp_path)))
    assert res.success
    assert res.metadata["truncated"] is True
    assert res.metadata["returned_lines"] == 10
    assert res.metadata["total_lines"] == 100


def test_file_read_grep_findet_zeilen(tmp_path):
    (tmp_path / "x.txt").write_text("foo=1\nbar=2\nfoobar=3\nbaz=4\n")
    res = _run(file_read._execute(
        {"path": "x.txt", "grep": "foo", "context_lines": 0}, _ctx(tmp_path)))
    assert res.success
    assert "foo=1" in res.output
    assert "foobar=3" in res.output
    assert "baz=4" not in res.output
    assert res.metadata["matches"] == 2


def test_file_read_grep_keine_treffer(tmp_path):
    (tmp_path / "x.txt").write_text("a\nb\nc")
    res = _run(file_read._execute({"path": "x.txt", "grep": "xyz"}, _ctx(tmp_path)))
    assert res.success
    assert "keine Treffer" in res.output
    assert res.metadata["matches"] == 0


def test_file_read_grep_ungueltiger_regex(tmp_path):
    (tmp_path / "x.txt").write_text("a")
    res = _run(file_read._execute({"path": "x.txt", "grep": "(unclosed"}, _ctx(tmp_path)))
    assert not res.success
    assert "Regex" in res.error or "regex" in res.error.lower()


# --- file_write ----------------------------------------------------------

def test_file_write_neue_datei(tmp_path):
    res = _run(file_write._execute({"path": "new.txt", "content": "hello"}, _ctx(tmp_path)))
    assert res.success
    assert (tmp_path / "new.txt").read_text() == "hello"
    assert res.metadata["bytes"] == 5


def test_file_write_ueberschreibt(tmp_path):
    (tmp_path / "x.txt").write_text("old")
    _run(file_write._execute({"path": "x.txt", "content": "new"}, _ctx(tmp_path)))
    assert (tmp_path / "x.txt").read_text() == "new"


def test_file_write_legt_parent_dirs_an(tmp_path):
    res = _run(file_write._execute({"path": "deep/nested/x.txt", "content": "y"}, _ctx(tmp_path)))
    assert res.success
    assert (tmp_path / "deep/nested/x.txt").read_text() == "y"


def test_file_write_pfad_ausserhalb_blockiert(tmp_path):
    res = _run(file_write._execute({"path": "/etc/evil.txt", "content": "x"}, _ctx(tmp_path)))
    assert not res.success
    assert not Path("/etc/evil.txt").exists()


def test_file_write_content_kein_string(tmp_path):
    res = _run(file_write._execute({"path": "x.txt", "content": 42}, _ctx(tmp_path)))
    assert not res.success
    assert "String" in res.error


# --- file_patch ----------------------------------------------------------

def test_file_patch_single_replace_happy_path(tmp_path):
    (tmp_path / "x.txt").write_text("foo bar baz")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "bar", "new_string": "BAR"}, _ctx(tmp_path)))
    assert res.success
    assert (tmp_path / "x.txt").read_text() == "foo BAR baz"
    assert res.metadata["replacements"] == 1


def test_file_patch_old_string_leer(tmp_path):
    (tmp_path / "x.txt").write_text("hi")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "", "new_string": "x"}, _ctx(tmp_path)))
    assert not res.success


def test_file_patch_old_gleich_new(tmp_path):
    (tmp_path / "x.txt").write_text("hi")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "hi", "new_string": "hi"}, _ctx(tmp_path)))
    assert not res.success
    assert "identisch" in res.error


def test_file_patch_datei_fehlt(tmp_path):
    res = _run(file_patch._execute(
        {"path": "missing.txt", "old_string": "a", "new_string": "b"}, _ctx(tmp_path)))
    assert not res.success


def test_file_patch_old_nicht_gefunden(tmp_path):
    (tmp_path / "x.txt").write_text("hello")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "xyz", "new_string": "abc"}, _ctx(tmp_path)))
    assert not res.success
    assert "nicht in der Datei" in res.error


def test_file_patch_mehrfach_ohne_replace_all_blockiert(tmp_path):
    (tmp_path / "x.txt").write_text("a\na\na")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "a", "new_string": "b"}, _ctx(tmp_path)))
    assert not res.success
    assert "3" in res.error
    assert (tmp_path / "x.txt").read_text() == "a\na\na"


def test_file_patch_replace_all(tmp_path):
    (tmp_path / "x.txt").write_text("a\na\na")
    res = _run(file_patch._execute(
        {"path": "x.txt", "old_string": "a", "new_string": "b", "replace_all": True},
        _ctx(tmp_path)))
    assert res.success
    assert res.metadata["replacements"] == 3
    assert (tmp_path / "x.txt").read_text() == "b\nb\nb"


def test_file_patch_pfad_ausserhalb_blockiert(tmp_path):
    res = _run(file_patch._execute(
        {"path": "../outside.txt", "old_string": "a", "new_string": "b"}, _ctx(tmp_path)))
    assert not res.success
