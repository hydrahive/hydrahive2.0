"""Recall- und Lehren-Blöcke für den System-Prompt (ausgelagert aus system_prompt.py, 14.11.2026)."""
from __future__ import annotations


def render_cards_block(cards: list[dict]) -> str:
    """Recall A: kompakter, klar als *abgeleitet* gelabelter Erinnerungs-Block für
    den gecachten Stable-Prompt. Getrennt vom kuratierten Memory; leerer String
    wenn keine brauchbaren Cards.

    Cards mit `groundedness='claimed'` werden zusätzlich als *unbelegt*
    gekennzeichnet: sie stammen überwiegend aus Assistant-Text, also aus einer
    Behauptung des Modells, nicht aus einem Tool-Ergebnis. `top_cards_for`
    sortiert sie bereits ans Ende — sie erscheinen hier nur, wenn nicht genug
    belegtes Material vorliegt. Dann soll das Modell den Unterschied sehen,
    statt die Behauptung als Tatsache zu übernehmen.
    """
    lines = []
    for c in cards:
        gist = (c.get("gist") or "").strip()
        if not gist:
            continue
        topics = c.get("topics") or []
        suffix = f"  ({', '.join(str(t) for t in topics[:4])})" if topics else ""
        unverified = " ⚠ unbelegt" if c.get("groundedness") == "claimed" else ""
        lines.append(f"- [{c.get('valence') or 'neutral'}{unverified}] {gist}{suffix}")
    if not lines:
        return ""
    return (
        "\n\n## Erinnerungen (automatisch verdichtet — keine kuratierten Notizen)\n"
        "Essenz früherer Sessions. Bei konkretem Bedarf via `datamining_*` tiefer graben.\n"
        + "\n".join(lines)
    )


def render_lessons_block(lessons: list[dict]) -> str:
    """Lehren mit Beleg (docs/specs/lehren-mit-beleg.md 10c): je Lehre Auslöser → Handlung, im wechselnden Teil
    (der gecachte Teil bleibt gleich). Leerer String ohne Lehren."""
    lines = []
    for le in lessons:
        n = int(le.get("confirmations") or 0)
        tag = ", ".join(x for x in (le.get("part"), le.get("confidence"), f"×{n} bestätigt" if n else "") if x)
        lines.append(f"- WENN {le.get('cue', '').strip()} → {le.get('lesson', '').strip()} [{tag}]")
    if not lines:
        return ""
    return "\n\nLehren aus früheren Aufgaben (mit Beleg) – prüfe, ob sie hier gelten:\n" + "\n".join(lines)


def render_search_block(cards: list[dict]) -> str:
    """Recall C: cue-getriggerte Treffer (zur aktuellen Eingabe), für den per-Turn/
    volatile Block. Trägt die session-id mit → Agent kann via `datamining_*` graben.
    Leerer String wenn keine brauchbaren Treffer."""
    lines = []
    for c in cards:
        gist = (c.get("gist") or "").strip()
        if not gist:
            continue
        src = c.get("source") if isinstance(c.get("source"), dict) else {}
        sid = (src or {}).get("session_id")
        ref = f"  [session {str(sid)[:8]}…]" if sid else ""
        lines.append(f"- {gist}{ref}")
    if not lines:
        return ""
    return (
        "\n\nRelevante frühere Erinnerungen zu deiner aktuellen Eingabe (abgeleitet):\n"
        + "\n".join(lines)
        + "\nBei Bedarf via `datamining_*` mit der session-id tiefer graben."
    )
