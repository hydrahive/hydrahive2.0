"""Memory v2 — Datenmodell und pure Functions ohne File-IO.

Migration alter Schemas, Confidence-Reinforcement, Expiry-Parsing,
Jaccard-Similarity, Project-Filter, Contradiction-Detection.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


MemoryEntry = dict[str, Any]
MemoryStore = dict[str, MemoryEntry]

_CONFIDENCE_DEFAULT = 0.5
_CONFIDENCE_STEP = 0.1  # Reinforcement: new = old + STEP * (1 - old)
_CONTRADICTION_THRESHOLD = 0.7  # Jaccard-Similarity ab der ein Widerspruch vermutet wird


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migrate_entry(value: Any) -> MemoryEntry:
    """Migriert alle früheren Schema-Versionen zum aktuellen Stand. Rückwärtskompatibel."""
    if isinstance(value, str):
        return {
            "content": value,
            "created_at": None,
            "updated_at": None,
            "expires_at": None,
            "confidence": _CONFIDENCE_DEFAULT,
            "reinforcements": 0,
            "last_reinforced_at": None,
            "is_latest": True,
            "superseded_by": None,
            "superseded_at": None,
            "supersedes": [],
            "project": None,  # None = global, in allen Projekten sichtbar
        }
    if isinstance(value, dict):
        entry = value.copy()
        entry.setdefault("confidence", _CONFIDENCE_DEFAULT)
        entry.setdefault("reinforcements", 0)
        entry.setdefault("last_reinforced_at", None)
        entry.setdefault("is_latest", True)
        entry.setdefault("superseded_by", None)
        entry.setdefault("superseded_at", None)
        entry.setdefault("supersedes", [])
        entry.setdefault("project", None)  # Bestehende Einträge → global
        return entry
    return _migrate_entry(str(value))


def _is_expired(entry: MemoryEntry) -> bool:
    expires_at = entry.get("expires_at")
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def is_expired(entry: MemoryEntry) -> bool:
    """Public alias für _is_expired — für externe Aufrufer."""
    return _is_expired(entry)


def _parse_expiry(value: str) -> str:
    """
    Parst relative Zeitangaben (+2h, +1d, +7d, +4w) oder gibt ISO-String zurück.
    Unterstützte Einheiten: h (Stunden), d (Tage), w (Wochen), m (Monate ~30d).
    """
    m = re.match(r"^\+(\d+)([hdwm])$", value.strip())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {
            "h": timedelta(hours=n),
            "d": timedelta(days=n),
            "w": timedelta(weeks=n),
            "m": timedelta(days=n * 30),
        }[unit]
        return (datetime.now(timezone.utc) + delta).isoformat()
    return value


def _reinforce_confidence(current: float) -> float:
    """Konvergierende Confidence-Erhöhung: new = old + STEP * (1 - old). Max 1.0."""
    return round(min(1.0, current + _CONFIDENCE_STEP * (1.0 - current)), 4)


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Token-basierte Jaccard-Similarity. Stopwörter (len <= 2) werden gefiltert.
    Gibt 0.0 zurück wenn eines der Texte nach dem Filter leer ist.
    """
    tokens_a = {t for t in text_a.lower().split() if len(t) > 2}
    tokens_b = {t for t in text_b.lower().split() if len(t) > 2}
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    return intersection / (len(tokens_a) + len(tokens_b) - intersection)


def _project_matches(entry: MemoryEntry, filter_project: str | None, active_project: str | None) -> bool:
    """
    Prüft ob ein Eintrag im gegebenen Projekt-Kontext sichtbar ist.

    Regeln:
    - filter_project="*"  → immer True (alle Projekte)
    - filter_project=X    → nur Einträge mit project=X oder project=None (global)
    - active_project=X    → wie filter_project=X, aber aus Session-Kontext
    - Kein Kontext        → nur globale Einträge (project=None)
    """
    entry_project = entry.get("project")  # None = global

    if filter_project == "*":
        return True

    if filter_project:
        return entry_project is None or entry_project == filter_project

    if active_project:
        return entry_project is None or entry_project == active_project

    return entry_project is None


def find_contradictions(data: MemoryStore, new_key: str, new_content: str) -> list[str]:
    """
    Prüft alle aktiven Einträge auf Ähnlichkeit mit dem neuen Content.
    Gibt Keys zurück deren Jaccard-Similarity >= _CONTRADICTION_THRESHOLD ist.
    Ignoriert: den neuen Key selbst, bereits veraltete Einträge, abgelaufene Einträge.
    """
    candidates = []
    for key, entry in data.items():
        if key == new_key:
            continue
        if not entry.get("is_latest", True):
            continue
        if _is_expired(entry):
            continue
        sim = _jaccard_similarity(new_content, entry.get("content", ""))
        if sim >= _CONTRADICTION_THRESHOLD:
            candidates.append(key)
    return candidates


def mark_superseded(data: MemoryStore, superseded_keys: list[str], by_key: str) -> None:
    """
    Markiert Einträge als veraltet (is_latest=False) in-place.
    Mutiert data direkt — Aufrufer ist für save() verantwortlich.
    """
    now = _now_iso()
    for key in superseded_keys:
        if key in data:
            data[key]["is_latest"] = False
            data[key]["superseded_by"] = by_key
            data[key]["superseded_at"] = now
