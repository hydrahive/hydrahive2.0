"""Prüfregeln für eine Lehre (Spec 10b) – reine Funktionen, ohne LLM und ohne Dateien.

`check(answer, record)` → (Lehre | None, Grund). Grund "" = gültig, "no_entry" = bewusst keine Lehre,
sonst ein Code, warum verworfen wurde.
"""
from __future__ import annotations

import hashlib
import re

PARTS = ("procedure", "tool", "skill", "prompt", "module", "user-preference")
MAX_LEN = 600
MIN_QUOTE = 20
SUPPORTING = ("helped", "hurt")
REQUIRED = ("cue", "lesson", "evidence", "quote")

# Allgemeinplätze aus dem Bestand (Spec 1) und der Harness²-Anleitung – solche Lehren feuern nie gezielt.
_PLATITUDES = re.compile(
    r"\b(be thorough|read (the )?files? before|verify (your |the )?changes|double[- ]check|"
    r"immer gründlich|gründlich prüfen|sorgfältig arbeiten)\b", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def key_of(cue: str) -> str:
    """Fingerabdruck des Auslösers: gleiche Situation (Groß-/Kleinschreibung, Leerraum egal) = gleicher Schlüssel."""
    return hashlib.sha256(_norm(cue).rstrip(".").encode("utf-8")).hexdigest()[:16]


def _confidence(value: str) -> str:
    v = _norm(value)
    if v.startswith(("high", "hoch")):
        return "high"
    if v.startswith(("medium", "mittel")):
        return "medium"
    return "low"


def _supported(turns) -> bool:
    return any(isinstance(t, dict) and _norm(str(t.get("verdict", ""))) in SUPPORTING for t in turns or [])


def check(answer: dict, record: str) -> tuple[dict | None, str]:
    raw = answer.get("lesson")
    if not isinstance(raw, dict):
        return None, "no_entry"
    les = {k: str(raw.get(k) or "").strip() for k in (*REQUIRED, "part", "confidence", "why")}
    for field in REQUIRED:
        if not les[field]:
            return None, "missing_" + field
        if len(les[field]) > MAX_LEN:
            return None, "too_long_" + field
    if les["part"] not in PARTS:
        return None, "bad_part"
    quote = _norm(les["quote"])
    if len(quote) < MIN_QUOTE:
        return None, "quote_too_short"
    if quote not in _norm(record):
        return None, "quote_not_found"
    if not _supported(answer.get("turns")):
        return None, "no_supporting_turn"
    if _PLATITUDES.search(les["lesson"]) or _PLATITUDES.search(les["cue"]):
        return None, "platitude"
    les["confidence"] = _confidence(les["confidence"])
    les["key"] = key_of(les["cue"])
    return les, ""
