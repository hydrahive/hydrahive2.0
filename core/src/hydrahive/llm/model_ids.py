"""Abgleich gespeicherter Modell-IDs mit den IDs einer Auswahlliste.

Dieselbe Modellwahl kann in der Config anders geschrieben stehen als in der
Liste, aus der die Oberfläche auswählt:

- `openrouter/google/gemini-…` gespeichert, Bild-Katalog listet `google/gemini-…`
- `text-embedding-3-small` gespeichert, Registry listet `openai/text-embedding-3-small`

Beide Schreibweisen bezeichnen dasselbe Modell und werden von den Verbrauchern
(Tools, Embedding) korrekt aufgelöst. Nur die Anzeige findet keine passende
Option. Der gespeicherte Wert wird deshalb NICHT umgeschrieben — beim Embedding
ist er zugleich Schlüssel des semantischen Index (`events.embedding_model`).
Stattdessen liefert die API zusätzlich die ID, die in der Liste steht.
"""
from __future__ import annotations

# Präfixe, die denselben Anbieter bezeichnen und beim Abgleich wegfallen dürfen.
_PROVIDER_PREFIXES = (
    "openrouter/", "openai/", "nvidia_nim/", "anthropic/", "openai-codex/",
    "ollama/", "gemini/", "mistral/", "groq/", "minimax/",
)


def _strip_once(model_id: str) -> str:
    for prefix in _PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


def _variants(model_id: str) -> set[str]:
    """Die ID selbst und jede Form nach schrittweisem Abschneiden der Präfixe.

    `openrouter/openai/whisper-1` -> {openrouter/openai/whisper-1,
    openai/whisper-1, whisper-1}. Nur so erkennt der Abgleich, dass
    `whisper-1` auf zwei verschiedene Listeneinträge passt.
    """
    out = {model_id}
    current = model_id
    while True:
        stripped = _strip_once(current)
        if stripped == current:
            return out
        out.add(stripped)
        current = stripped


def match_listed_id(value: str, listed_ids: list[str]) -> str:
    """Liefert die ID aus `listed_ids`, die `value` bezeichnet, sonst "".

    Reihenfolge: exakter Treffer; danach genau EIN Treffer, bei dem ein
    Anbieter-Präfix auf einer der beiden Seiten wegfällt. Mehrdeutige
    Treffer werden nicht geraten — eine falsch angezeigte Auswahl würde beim
    nächsten Speichern ein anderes Modell festschreiben.
    """
    value = (value or "").strip()
    if not value or not listed_ids:
        return ""
    if value in listed_ids:
        return value
    if value.startswith("local:"):
        return ""  # Routing-Entscheidung, nur exakt

    wanted = _variants(value)
    hits = [
        listed for listed in listed_ids
        if not listed.startswith("local:") and _variants(listed) & wanted
    ]
    return hits[0] if len(hits) == 1 else ""
