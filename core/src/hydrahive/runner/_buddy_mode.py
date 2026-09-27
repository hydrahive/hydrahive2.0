"""Gesprächsmodus des Buddys (Auswahl „Modus“ auf der Buddy-Seite).

Der Modus gilt pro Session (`session.metadata['buddy_mode']`) und hängt zur
Laufzeit einen kurzen Stil-Hinweis an den Buddy-Prompt — wie der Emote-Hinweis,
nicht in den editierbaren Prompt gebacken. „normal“ bzw. kein Wert = kein Hinweis.
Nur für den Buddy (is_buddy); normale Agenten bleiben unverändert.
"""
from __future__ import annotations

BUDDY_MODES: dict[str, str] = {
    "focus": (
        "Fokus-Modus: Bleib strikt bei der aktuellen Aufgabe. Keine Abschweifungen, "
        "kein Smalltalk, keine ungefragten Zusatzvorschläge. Sachlich und zielgerichtet."
    ),
    "humor": (
        "Humor-Modus: Sei ruhig verspielt und witzig, mit Wortspielen und einem "
        "Augenzwinkern. Fakten und Ergebnisse bleiben trotzdem korrekt und vollständig."
    ),
    "brief": (
        "Kurz-Modus: Antworte so knapp wie möglich — ein bis drei Sätze oder eine "
        "kurze Liste. Ausführlicher nur, wenn ausdrücklich danach gefragt wird."
    ),
}
VALID_MODES = frozenset({"normal", *BUDDY_MODES})


def with_buddy_mode(base_prompt: str, *, is_buddy: bool, mode: str | None) -> str:
    """Hängt den Stil-Hinweis des Modus an, wenn es der Buddy ist."""
    hint = BUDDY_MODES.get(mode or "") if is_buddy else None
    if not hint:
        return base_prompt
    return f"{base_prompt}\n\n## Gesprächsmodus\n{hint}"
