"""Compact bei riesigen Einzelnachrichten (Task 5406d099, Befund Berkan 27.10.2026).

Befund: Ein Projekt-Chat bei 2,6 Mio. Tokens – jedes Compact scheiterte mit „prompt is too long: 6.043.166 tokens >
1.000.000“. Ursache: (1) serialize kürzte nur Tool-Ergebnisse; Bilder/PDFs (base64) und lange Texte gingen ungekürzt
in die Zusammenfassung. (2) Das Teilen in Stücke schnitt nur ZWISCHEN Nachrichten – eine einzelne riesige Nachricht
blieb ein Stück und ging ungeprüft ans Modell. Auf .2 gefunden: ein Bild (2,78 MB) = 2,3 Mio. „Tokens“ in einem Stück.
"""
from __future__ import annotations

import asyncio
import base64

import pytest

from hydrahive.compaction import summarize as summ
from hydrahive.compaction._chunking import split_at_message_boundaries
from hydrahive.compaction.serialize import serialize_for_summary
from hydrahive.compaction.tokens import estimate_dense_text
from hydrahive.db.messages import Message


def _msg(role, content, i=0):
    return Message(id=f"m{i}", session_id="s", role=role, content=content, created_at="2026-10-27T00:00:00Z")


B64 = base64.b64encode(b"\xff\xd8\xff" + b"x" * 2_000_000).decode()   # Datei: 2.000.003 Bytes = 1,9 MB
GONE = B64[:5_000]   # ein Stück der Daten – darf nirgends mehr auftauchen


# --- 1. Bilder, PDFs und andere Nicht-Text-Blöcke -----------------------------------------------------------------

def test_bild_wird_platzhalter():
    m = _msg("user", [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": B64}},
                      {"type": "text", "text": "Was steht auf dem Foto?"}])
    out = serialize_for_summary([m])
    assert GONE not in out
    assert "[Bild: image/jpeg, 1,9 MB]" in out
    assert "Was steht auf dem Foto?" in out
    assert len(out) < 500


def test_pdf_wird_platzhalter_mit_namen():
    m = _msg("user", [{"type": "document", "title": "Kaufvertrag.pdf",
                       "source": {"type": "base64", "media_type": "application/pdf", "data": B64}}])
    out = serialize_for_summary([m])
    assert GONE not in out
    assert "[Dokument: Kaufvertrag.pdf, application/pdf, 1,9 MB]" in out


def test_bild_als_url_ohne_daten():
    m = _msg("user", [{"type": "image", "source": {"type": "url", "url": "https://x.test/a.png"}}])
    out = serialize_for_summary([m])
    assert "[Bild: https://x.test/a.png]" in out


def test_bild_im_tool_ergebnis():
    m = _msg("user", [{"type": "tool_result", "tool_use_id": "toolu_12345678", "content": [
        {"type": "text", "text": "Screenshot:"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": B64}}]}])
    out = serialize_for_summary([m])
    assert GONE not in out
    assert "[Bild: image/png, 1,9 MB]" in out and "Screenshot:" in out


def test_bild_beim_assistenten():
    m = _msg("assistant", [{"type": "text", "text": "Hier das Bild"},
                           {"type": "image", "source": {"type": "base64", "media_type": "image/webp", "data": B64}}])
    out = serialize_for_summary([m])
    assert GONE not in out and "[Bild: image/webp, 1,9 MB]" in out


def test_unbekannte_bloecke_beim_assistenten_werden_nicht_ausgeschrieben():
    """codex_reasoning u. ä. (auf .2 7.720 Stück): verschlüsselt/intern, für die Zusammenfassung wertlos."""
    m = _msg("assistant", [{"type": "codex_reasoning", "encrypted_content": "Z" * 500_000},
                           {"type": "text", "text": "Fertig."}])
    out = serialize_for_summary([m])
    assert "Z" * 1000 not in out and "Fertig." in out


def test_unbekannte_bloecke_beim_nutzer_werden_gekuerzt():
    m = _msg("user", [{"type": "seltsam", "payload": "Q" * 500_000}])
    out = serialize_for_summary([m])
    assert len(out) < 10_000


# --- 2. Lange Texte je Block gekürzt ------------------------------------------------------------------------------

_BIG = "A" * 2_000_000
# Kurze IDs: Ohne sie steckt der 2-MB-Text im Testnamen – `pytest -v` in der CI brauchte dafür über eine Stunde
# pro Name und lief 6 h bis zum Abbruch (27.10.2026).
_LONG_CASES = {
    "user-text": ("user", lambda: _BIG),
    "user-block": ("user", lambda: [{"type": "text", "text": _BIG}]),
    "assistant-text": ("assistant", lambda: _BIG),
    "assistant-block": ("assistant", lambda: [{"type": "text", "text": _BIG}]),
    "assistant-thinking": ("assistant", lambda: [{"type": "thinking", "thinking": _BIG}]),
    "system": ("system", lambda: _BIG),
}


@pytest.mark.parametrize("case", sorted(_LONG_CASES))
def test_lange_texte_werden_gekuerzt(case):
    from hydrahive.compaction.serialize import TEXT_BLOCK_LIMIT
    role, make = _LONG_CASES[case]
    out = serialize_for_summary([_msg(role, make())])
    assert len(out) < TEXT_BLOCK_LIMIT + 500
    assert "[gekürzt:" in out


def test_kurze_texte_bleiben_unveraendert():
    out = serialize_for_summary([_msg("user", "Kurze Frage zum Kaufvertrag?"),
                                 _msg("assistant", [{"type": "text", "text": "Kurze Antwort."}], 1)])
    assert out == "[User]: Kurze Frage zum Kaufvertrag?\n[Assistant]: Kurze Antwort."


def test_text_limit_grosszuegig():
    """Texte sollen nicht unnötig verloren gehen – nur echte Riesen werden gekürzt."""
    from hydrahive.compaction.serialize import TEXT_BLOCK_LIMIT
    assert TEXT_BLOCK_LIMIT >= 50_000
    out = serialize_for_summary([_msg("user", "B" * 40_000)])
    assert "[gekürzt:" not in out


# --- 3. Teilen in Stücke: garantiert jedes Stück ≤ Grenze ---------------------------------------------------------

def test_riesige_nachricht_mit_vielen_zeilen_wird_geteilt():
    big = "[User]: " + "\n".join(f"Zeile {i} des Schriftsatzes ..." for i in range(300_000))
    chunks = split_at_message_boundaries("[Assistant]: kurz\n" + big + "\n[Assistant]: Antwort", 640_000)
    assert len(chunks) > 1
    assert max(estimate_dense_text(c) for c in chunks) <= 640_000


def test_einzeilige_riesen_nachricht_wird_mitten_in_der_zeile_geteilt():
    chunks = split_at_message_boundaries("[User]: a\n[Tool]: " + "x" * 8_000_000 + "\n[User]: b", 640_000)
    assert max(estimate_dense_text(c) for c in chunks) <= 640_000
    assert "".join(chunks).count("x") == 8_000_000           # nichts verloren


def test_teilen_verliert_nichts_und_haelt_reihenfolge():
    lines = [f"[User]: frage {i}" if i % 3 == 0 else f"inhalt {i} " + "y" * 50 for i in range(5000)]
    text = "\n".join(lines)
    chunks = split_at_message_boundaries(text, 2_000)
    assert max(estimate_dense_text(c) for c in chunks) <= 2_000
    assert "\n".join(chunks) == text


def test_kleiner_text_ein_stueck():
    assert split_at_message_boundaries("[User]: hallo\n[Assistant]: hi", 10_000) == ["[User]: hallo\n[Assistant]: hi"]


# --- 4. Schutz vor dem Aufruf --------------------------------------------------------------------------------------

def _fake_llm(monkeypatch, calls):
    from hydrahive.runner import llm_bridge

    async def fake(*, model, system_prompt, messages, tools, temperature, max_tokens):
        calls.append(sum(len(m["content"]) for m in messages) + len(system_prompt))
        return [{"type": "text", "text": "ZUSAMMENFASSUNG"}], None, None

    monkeypatch.setattr(llm_bridge, "call_with_tools", fake)


def test_summarize_riesige_einzelnachricht_alle_aufrufe_passen(monkeypatch):
    calls: list[int] = []
    _fake_llm(monkeypatch, calls)
    hist = "[User]: a\n[Tool result 1]: " + "x" * 8_000_000 + "\n[User]: b"
    out = asyncio.run(summ.summarize(model="claude-sonnet-4-6", serialized_history=hist))
    assert out == "ZUSAMMENFASSUNG"
    window_chars = int(1_000_000 * 1.2)
    assert calls and max(calls) < window_chars                 # kein Aufruf größer als das Fenster


def test_aufruf_groesser_als_fenster_wird_nicht_gesendet(monkeypatch):
    """Letzte Sicherung: auch wenn vorher etwas schiefgeht – nie einen zu großen Prompt abschicken (kostet nur)."""
    calls: list[int] = []
    _fake_llm(monkeypatch, calls)
    with pytest.raises(summ.SummaryTooLarge):
        asyncio.run(summ._single_summarize("claude-sonnet-4-6", "sys", "x" * 3_000_000, None, "", 4096))
    assert calls == []


def test_vorige_zusammenfassung_zaehlt_mit(monkeypatch):
    """Eine riesige frühere Zusammenfassung darf das erste Stück nicht über das Fenster schieben."""
    calls: list[int] = []
    _fake_llm(monkeypatch, calls)
    prev = "P" * 900_000
    hist = "\n".join(f"[User]: frage {i} " + "z" * 200 for i in range(20_000))
    asyncio.run(summ.summarize(model="claude-sonnet-4-6", serialized_history=hist, previous_summary=prev))
    assert calls and max(calls) < int(1_000_000 * 1.2)


def test_merge_groesser_als_fenster_wird_nicht_gesendet(monkeypatch):
    """Auch der Zusammenführ-Schritt prüft vor dem Senden (eine einzelne riesige Teil-Zusammenfassung)."""
    calls: list[int] = []
    _fake_llm(monkeypatch, calls)
    with pytest.raises(summ.SummaryTooLarge):
        asyncio.run(summ._merge_summaries("claude-sonnet-4-6", ["S" * 3_000_000], 4096, 10_000_000))
    assert calls == []


def test_merge_einer_einzelnen_riesigen_teilzusammenfassung_endet(monkeypatch):
    """Ohne Abbruchbedingung rief sich der Merge bei EINER zu großen Teil-Zusammenfassung endlos selbst auf."""
    import sys
    calls: list[int] = []
    _fake_llm(monkeypatch, calls)
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(200)
    try:
        with pytest.raises(summ.SummaryTooLarge):
            asyncio.run(summ._merge_summaries("claude-sonnet-4-6", ["S" * 3_000_000], 4096, 1_000))
    finally:
        sys.setrecursionlimit(old)
