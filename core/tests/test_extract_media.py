"""Regressionstest für extract_media (runner/_media.py).

Bug: save_prompt liefert {"saved": True} (bool). extract_media iterierte das
"saved"-Feld blind (`for s in output.get("saved") or []`) → bei einem bool
`for s in True` → TypeError: 'bool' object is not iterable. Der Crash kippte
den Tool-Use-Turn, bevor der tool_result-Block in die History geschrieben war
→ "Truncation im vorigen Turn" beim Folge-Turn.

Hier wird sichergestellt, dass nicht-iterierbare Werte in saved/all_files
sauber ignoriert werden und echte Listen weiterhin funktionieren.
"""
from __future__ import annotations

from pathlib import Path

from hydrahive.runner._media import extract_media
from hydrahive.tools.base import ToolResult


def test_saved_bool_crasht_nicht():
    """save_prompt-Form {"saved": True} darf keinen TypeError werfen."""
    r = ToolResult.ok({"id": "abc", "title": "Track IV", "saved": True})
    assert extract_media(r, Path("/var/lib/hydrahive2")) == []


def test_all_files_nicht_iterierbar_crasht_nicht():
    r = ToolResult.ok({"all_files": 5})
    assert extract_media(r, None) == []


def test_saved_liste_mit_audio_wird_gefunden():
    """Gegenprobe: echte Pfad-Liste (generate_music) liefert Media.

    Pfad unter /tmp/, weil das in jeder Umgebung in servable_prefixes liegt
    (im Test wird der Prefix per conftest auf ein tmp-Verzeichnis gesetzt).
    """
    r = ToolResult.ok({"saved": ["/tmp/x.mp3"]})
    media = extract_media(r, None)
    assert media == [{"kind": "audio", "path": "/tmp/x.mp3"}]


def test_output_ohne_saved_key_ist_leer():
    r = ToolResult.ok({"prompts": [{"id": "x"}], "count": 1})
    assert extract_media(r, None) == []


def test_fehler_result_liefert_keine_media():
    r = ToolResult.fail("kaputt")
    assert extract_media(r, None) == []


def test_saved_mit_nicht_string_elementen_wird_gefiltert():
    """Mischliste: nur String-Pfade zählen, Zahlen/None werden ignoriert."""
    r = ToolResult.ok({"saved": ["/tmp/a.png", 42, None]})
    media = extract_media(r, None)
    assert media == [{"kind": "image", "path": "/tmp/a.png"}]
