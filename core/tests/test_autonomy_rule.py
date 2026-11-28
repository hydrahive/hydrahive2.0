"""Till 28.11.: Läufe ohne Nutzer vor dem Bildschirm (Auftrag, Hintergrund, Zustellung) arbeiten durch statt zu fragen.

Kleinkram (Farbe, Name, Reihenfolge, Lösungsweg) entscheidet der Agent selbst und schreibt es in den Bericht. Stehen bleiben
nur bei echten Hindernissen. Im direkten Chat bleibt die kurze Rückfrage erlaubt.
"""
from __future__ import annotations

from hydrahive.runner._autonomy_rule import AUTONOMY_RULE, with_autonomy_rule


def test_regel_haengt_nur_an_unbeaufsichtigten_laeufen():
    for origin in ("delegation", "handoff"):
        assert AUTONOMY_RULE in with_autonomy_rule("BASIS", origin)
    for origin in ("chat", "other", None):
        assert with_autonomy_rule("BASIS", origin) == "BASIS"


def test_regel_nennt_die_echten_hindernisse_und_den_bericht():
    for stichwort in ("Zugang", "unumkehrbar", "Prod", "Kosten", "Sicherheit", "Bericht", "selbst"):
        assert stichwort in AUTONOMY_RULE, stichwort


def test_zustelltext_verlangt_keine_rueckfrage_mehr():
    from hydrahive.runner._delegation_message import FOOTER
    assert "nur nach Rückfrage" not in FOOTER
    assert "zu Ende" in FOOTER
