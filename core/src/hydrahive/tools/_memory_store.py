from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hydrahive.settings import settings


# ---------------------------------------------------------------------------
# Typen
# ---------------------------------------------------------------------------

MemoryEntry = dict[str, Any]
MemoryStore = dict[str, MemoryEntry]

_CONFIDENCE_DEFAULT = 0.5
_CONFIDENCE_STEP = 0.1  # Reinforcement: new = old + STEP * (1 - old)
_CONTRADICTION_THRESHOLD = 0.7  # Jaccard-Similarity ab der ein Widerspruch vermutet wird


# ---------------------------------------------------------------------------
# Internes
# ---------------------------------------------------------------------------

def _memory_file(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "memory.json"


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


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def load(agent_id: str) -> MemoryStore:
    """Lädt die Memory-Datei und migriert alte Einträge automatisch."""
    path = _memory_file(agent_id)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {k: _migrate_entry(v) for k, v in raw.items()}


def load_active(
    agent_id: str,
    filter_project: str | None = None,
    active_project: str | None = None,
) -> MemoryStore:
    """Alias für load_filtered(include_superseded=False). Für Abwärtskompatibilität."""
    return load_filtered(agent_id, filter_project=filter_project, active_project=active_project)


def save(agent_id: str, data: MemoryStore) -> None:
    path = _memory_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_entry(agent_id: str, key: str) -> MemoryEntry | None:
    """
    Gibt den vollständigen MemoryEntry zurück, oder None wenn nicht vorhanden / abgelaufen.
    Kein Projekt-Filter — expliziter Schlüssel-Lookup ignoriert Projekt-Grenzen.
    """
    entry = load(agent_id).get(key)
    if entry is None:
        return None
    if _is_expired(entry):
        return None
    return entry


def read_key(agent_id: str, key: str) -> str | None:
    """Gibt nur den content-Wert zurück, oder None wenn nicht vorhanden / abgelaufen."""
    entry = read_entry(agent_id, key)
    return entry.get("content") if entry is not None else None


def write_key(
    agent_id: str,
    key: str,
    content: str,
    expires_at: str | None = None,
    confidence: float | None = None,
    project: str | None = None,
    check_contradictions: bool = True,
) -> tuple[MemoryEntry, list[str]]:
    """
    Schreibt einen Memory-Eintrag. Gibt (entry, superseded_keys) zurück.

    project: Projekt-Zuordnung. None = global (in allen Projekten sichtbar).
             Bei Updates: project wird NUR aktualisiert wenn explizit übergeben —
             bestehende Projekt-Zuordnung bleibt sonst erhalten.
    """
    data = load(agent_id)
    now = _now_iso()
    parsed_expiry = _parse_expiry(expires_at) if expires_at else None

    superseded_keys: list[str] = []
    if check_contradictions:
        superseded_keys = find_contradictions(data, key, content)
        if superseded_keys:
            mark_superseded(data, superseded_keys, by_key=key)

    existing = data.get(key)
    if existing and isinstance(existing, dict):
        old_conf = existing.get("confidence", _CONFIDENCE_DEFAULT)
        existing["content"] = content
        existing["updated_at"] = now
        existing["confidence"] = _reinforce_confidence(old_conf)
        existing["reinforcements"] = existing.get("reinforcements", 0) + 1
        existing["last_reinforced_at"] = now
        existing["is_latest"] = True
        existing["supersedes"] = existing.get("supersedes", []) + superseded_keys
        if parsed_expiry is not None:
            existing["expires_at"] = parsed_expiry
        if project is not None:
            existing["project"] = project
        data[key] = existing
    else:
        init_confidence = confidence if confidence is not None else _CONFIDENCE_DEFAULT
        data[key] = {
            "content": content,
            "created_at": now,
            "updated_at": now,
            "expires_at": parsed_expiry,
            "confidence": round(max(0.0, min(1.0, init_confidence)), 4),
            "reinforcements": 0,
            "last_reinforced_at": None,
            "is_latest": True,
            "superseded_by": None,
            "superseded_at": None,
            "supersedes": superseded_keys,
            "project": project,
        }

    save(agent_id, data)
    return data[key], superseded_keys


def delete_key(agent_id: str, key: str) -> bool:
    data = load(agent_id)
    if key not in data:
        return False
    del data[key]
    save(agent_id, data)
    return True


def list_keys(
    agent_id: str,
    filter_project: str | None = None,
    active_project: str | None = None,
) -> list[str]:
    """Gibt alle aktiven Keys zurück, optional Projekt-gefiltert."""
    data = load(agent_id)
    return sorted(
        k for k, v in data.items()
        if not _is_expired(v)
        and v.get("is_latest", True)
        and _project_matches(v, filter_project, active_project)
    )


def cleanup_expired(agent_id: str) -> int:
    """
    Löscht alle abgelaufenen Einträge. Gibt Anzahl gelöschter Einträge zurück.
    Veraltete (is_latest=False) Einträge bleiben erhalten — sie sind History.
    """
    data = load(agent_id)
    expired_keys = [k for k, v in data.items() if _is_expired(v)]
    if not expired_keys:
        return 0
    for k in expired_keys:
        del data[k]
    save(agent_id, data)
    return len(expired_keys)


def load_filtered(
    agent_id: str,
    filter_project: str | None = None,
    active_project: str | None = None,
    include_superseded: bool = False,
) -> MemoryStore:
    """
    Zentraler Filter-Einstieg für search_memory und ähnliche Aufrufer.
    Kombiniert Expired-, Superseded- und Projekt-Filter in einem Aufruf.

    include_superseded=True → is_latest=False Einträge werden eingeschlossen.
    """
    data = load(agent_id)
    return {
        k: v for k, v in data.items()
        if not _is_expired(v)
        and (include_superseded or v.get("is_latest", True))
        and _project_matches(v, filter_project, active_project)
    }
