"""Durcharbeiten statt fragen für unbeaufsichtigte Läufe (Till 28.11.2026).

„Ich bekomme den Horror, wenn ich wiederkomme und gefragt wurde, ob der Punkt grün oder blau sein soll, und deswegen
nichts gemacht wurde.“ Läufe, vor denen kein Mensch sitzt (Zustellung von Ergebnissen, eingehende Aufträge), bekommen
diesen Block am stabilen Prompt-Teil – einmal je Lauf, also cache-freundlich. Im direkten Chat (`chat`) bleibt die kurze
Rückfrage erlaubt: da sitzt der Nutzer davor.
"""
from __future__ import annotations

UNATTENDED_ORIGINS = frozenset({"delegation", "handoff"})

AUTONOMY_RULE = (
    "## Arbeitsweise ohne Nutzer\n"
    "Gerade sitzt niemand vor dem Bildschirm. Arbeite den Auftrag vollständig zu Ende.\n"
    "- Entscheide selbst, was sich zurückdrehen lässt: Gestaltung, Farben, Namen, Reihenfolge, Lösungsweg, kleine "
    "Unklarheiten. Nimm die vernünftigste Wahl und schreib jede solche Entscheidung in den Abschlussbericht.\n"
    "- Stehen bleiben nur bei echten Hindernissen: Zugang oder Passwort fehlt; etwas wäre zerstörerisch oder "
    "unumkehrbar (Daten löschen, Force-Push); Eingriff auf Prod-Servern oder Neustart; echte Kosten oder Zahlungen; "
    "Sicherheits- oder Rechte-Entscheidungen.\n"
    "- Auch dann den ganzen Rest fertig machen und im Bericht klar sagen, was offen ist und warum.\n"
    "- Scheitert ein Unterauftrag oder läuft ab, selbst neu oder kleiner geschnitten vergeben."
)


def with_autonomy_rule(base_prompt: str, origin: str | None) -> str:
    """Hängt den Block an, wenn der Lauf unbeaufsichtigt ist (Zustellung, eingehender Auftrag)."""
    return f"{base_prompt}\n\n{AUTONOMY_RULE}" if origin in UNATTENDED_ORIGINS else base_prompt
