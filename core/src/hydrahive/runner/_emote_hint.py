"""Hydra-Emote-Hinweis für den Buddy-System-Prompt.

Das Frontend (`frontend/src/features/chat/hydraEmotes.ts`) rendert `:hydra-NAME:`
als kleines Bild. Damit der Buddy die Emotes von selbst nutzt (statt Unicode),
hängt der Runner diesen Hinweis nur an den Buddy-Prompt an — zur Laufzeit, nicht
in den editierbaren Prompt gebacken.

Die Namensliste spiegelt EMOTE_NAMES aus dem Frontend. Bei Änderungen dort hier
nachziehen (selten — Emotes ändern sich kaum).
"""
from __future__ import annotations

EMOTE_NAMES = [
    "smile", "grin", "lol", "tears", "rofl", "wink", "kiss", "smirk", "cool",
    "sunglasses", "love", "plead", "hmm", "monocle", "wow", "hushed", "scared",
    "explode", "angry", "unamused", "facepalm", "cry", "nerd", "money", "fire",
    "idea", "party", "thumbsup", "sleepy", "neutral", "shush", "zipper", "devil",
    "angel", "sick", "cowboy", "alien", "drool", "rocket", "pirate", "ninja",
    "wizard", "king", "chef", "hacker", "detective", "builder", "coffee", "borg",
    "brainfull", "doublefacepalm",
    # Symbole & Objekte (datengetrieben — meistgenutzte Emojis der Agenten)
    "checkmark", "cross", "warning", "chart", "vulcan", "muscle", "lobster",
    "trophy", "sparkle", "lightning", "shield", "search", "bug", "brain", "bulb",
    "robot", "refresh", "handshake", "wave", "eyes", "books", "graduation", "lab",
    "palette", "hammer", "wrench", "plug", "globe", "moon", "bee", "clapper",
    "theater",
    # Reaktionen & Objekte (Batch 3)
    "thumbsdown", "ok", "fist", "clap", "crossfingers", "shrug", "grimace",
    "woozy", "scream", "starstruck", "sweat-smile", "raised-eyebrow", "question",
    "boom", "skull", "siren", "stop", "confetti", "gift", "dice", "gold",
    "crystal", "dna", "dragon", "gear", "laptop", "mic", "speaker", "speech",
    "spy", "tophat", "popcorn",
]

HYDRA_EMOTE_HINT = (
    "\n\n## Hydra-Emotes\n"
    "Du kannst Hydra-Emoticons verwenden: schreib `:hydra-NAME:` und es wird im "
    "Chat als kleines Bild gerendert. Setz sie **sparsam** und passend ein "
    "(nicht in jeder Zeile, lieber als gelegentliche Pointe). Verfügbare Namen:\n"
    + ", ".join(EMOTE_NAMES) + ".\n"
    'Beispiele: "Läuft! :hydra-thumbsup:" · "Uff :hydra-facepalm:" · '
    '"Geheime Mission :hydra-ninja:".'
)


def with_emote_hint(base_prompt: str, *, is_buddy: bool) -> str:
    """Hängt den Emote-Hinweis an, wenn es der Buddy ist; sonst unverändert."""
    if not is_buddy:
        return base_prompt
    return base_prompt + HYDRA_EMOTE_HINT
