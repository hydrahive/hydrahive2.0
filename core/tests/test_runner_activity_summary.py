"""Kurzfassung des letzten Tool-Ergebnisses für die Sprechblase im Agenten-Büro (Spec agent-office.md §1)."""
from __future__ import annotations

from hydrahive.runner._activity_summary import summarize_result_blocks


def test_text_wird_gekuerzt_auf_120():
    blocks = [{"type": "tool_result", "content": "A" * 300}]
    out = summarize_result_blocks(blocks)
    assert len(out) <= 120


def test_fehler_wird_markiert():
    blocks = [{"type": "tool_result", "content": "whatever", "is_error": True}]
    assert summarize_result_blocks(blocks).startswith("Fehler: ")


def test_leere_bloecke_leerer_string():
    assert summarize_result_blocks([]) == ""
    assert summarize_result_blocks([{"type": "tool_result", "content": ""}]) == ""


def test_liste_als_content_wird_text_extrahiert():
    blocks = [{"type": "tool_result", "content": [{"type": "text", "text": "Zeile 1"}, {"type": "image_url"}]}]
    assert summarize_result_blocks(blocks) == "Zeile 1"


def test_mehrzeilig_nimmt_erste_zeile():
    blocks = [{"type": "tool_result", "content": "Zeile 1\nZeile 2\nZeile 3"}]
    assert summarize_result_blocks(blocks) == "Zeile 1"
