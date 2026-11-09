"""Gemessene Prompt-Größe des letzten LLM-Aufrufs als zweiter Compaction-Trigger.

Warum: Der Trigger schätzt die History mit 3,5 Zeichen pro Token. Bei dichtem Inhalt (JSON, Tool-Ergebnisse,
Code) liegt der echte Wert deutlich darüber. Am 09.11.2026 schätzte er 685k Tokens, Anthropic meldete 998k, und
die Session lief in „prompt is too long: 1001452 tokens > 1000000“, ohne dass die Compaction je zündete.
Solange die Sitzung auf einem 372k-Modell lief, fiel das nicht auf, weil schon die Schätzung über der Schwelle lag.

Die Provider liefern die echte Zahl pro Aufruf; sie steht in der Metadata jeder Assistant-Nachricht.
"""
from __future__ import annotations

from typing import Any

from hydrahive.compaction.tokens import estimate_message

# OpenAI/Codex zählt gecachte Tokens IN input_tokens mit. Anthropic weist sie getrennt aus.
_INPUT_INCLUDES_CACHE_PREFIXES = ("openai-codex/",)


def prompt_tokens_from_metadata(meta: dict[str, Any] | None) -> int:
    """Gesamtgröße des gesendeten Prompts laut Provider. 0, wenn keine Messung vorliegt."""
    if not meta:
        return 0
    try:
        inp = int(meta.get("input_tokens") or 0)
        cache_read = int(meta.get("cache_read_tokens") or 0)
        cache_creation = int(meta.get("cache_creation_tokens") or 0)
    except (TypeError, ValueError):
        return 0
    model = str(meta.get("model") or "")
    if model.startswith(_INPUT_INCLUDES_CACHE_PREFIXES):
        return inp
    return inp + cache_read + cache_creation


def measured_history_tokens(history: list, *, model: str, compacted_at: str | None) -> int:
    """Echte Prompt-Größe des letzten Aufrufs plus Schätzung für alles, was seitdem dazukam.

    Grundlage ist die jüngste Assistant-Antwort desselben Modells: ihre gemessene Prompt-Größe, dazu die
    geschätzten Nachrichten ab ihr (ihre eigene Ausgabe, neue Tool-Ergebnisse, neue Nutzernachricht).
    Liefert 0, wenn keine verwertbare Messung vorliegt; der Aufrufer nutzt dann nur die Schätzung.

    Zählt nur Messungen NACH der letzten Compaction. Behaltene ältere Nachrichten tragen noch die Größe von
    vor der Compaction und würden sonst sofort die nächste Compaction auslösen (Schleife).
    Ein anderes Modell zählt nicht: Tokenizer und Fenster unterscheiden sich.
    """
    for index in range(len(history) - 1, -1, -1):
        message = history[index]
        if getattr(message, "role", None) != "assistant":
            continue
        if compacted_at and (getattr(message, "created_at", "") or "") <= compacted_at:
            return 0
        meta = getattr(message, "metadata", None) or {}
        if meta.get("model") != model:
            return 0
        measured = prompt_tokens_from_metadata(meta)
        if measured <= 0:
            return 0
        return measured + sum(estimate_message(m) for m in history[index:])
    return 0
