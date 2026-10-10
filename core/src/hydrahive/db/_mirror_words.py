"""Anfrage für die Datamining-Wortsuche in Wörter zerlegen (docs/specs/datamining-gesamtindex.md §3.3).

Übernommen aus dem verworfenen Branch ``feat/datamining-wortsuche`` (09.10.): Die Zerlegung war gut, nur das
Kandidaten-Fenster („2000 neueste“) verlor alte Erinnerungen. Gesucht wird jetzt über den Gesamtindex.
"""
from __future__ import annotations

import re

MAX_WORDS = 6          # die längsten Wörter tragen am meisten Bedeutung
MIN_LEN = 3

# Füllwörter (deutsch, häufig in Fragen an Agenten) – tragen nichts zur Suche bei. Gleiche Liste wie im Messrahmen.
STOP = frozenset("""aber alle allem als also auch dann das dass dein deine dem den der des die dies diese diesem dieser
 doch ein eine einem einen einer eines etwa euch habe haben hat hatte hatten hier ihr ihre immer ist jetzt kann keine
 konnte machen mal mein meine mich mit nach nicht noch nochmal oder sein seine sich sie sind sollte und uns unser unsere
 unter viel vom von war waren warum was weil welche welchen welcher wenn wer werden wie wieder wir wird wollten wurde
 wurden zum zur über the and for with""".split())

_WORD = re.compile(r"[\w.\-]+", re.UNICODE)


def split_words(q: str) -> list[str]:
    """Wörter ab 3 Zeichen ohne Füllwörter, klein, ohne Dubletten, die 6 längsten (gleich lang: Textreihenfolge)."""
    seen: dict[str, None] = {}
    for w in _WORD.findall((q or "").lower()):
        w = w.strip("._-")
        if len(w) >= MIN_LEN and w not in STOP:
            seen.setdefault(w, None)
    words = list(seen)
    return sorted(words, key=lambda w: (-len(w), words.index(w)))[:MAX_WORDS]
