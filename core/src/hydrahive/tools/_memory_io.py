"""Memory v2 — File-IO und Public-API für Read/Write/List."""
from __future__ import annotations

import json
from pathlib import Path

from hydrahive.settings import settings
from hydrahive.tools._memory_model import (
    _CONFIDENCE_DEFAULT,
    _is_expired,
    _migrate_entry,
    _now_iso,
    _parse_expiry,
    _project_matches,
    _reinforce_confidence,
    MemoryEntry,
    MemoryStore,
    find_contradictions,
    mark_superseded,
)


def _memory_file(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "memory.json"


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


def save(agent_id: str, data: MemoryStore) -> None:
    path = _memory_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_active(
    agent_id: str,
    filter_project: str | None = None,
    active_project: str | None = None,
) -> MemoryStore:
    """Alias für load_filtered(include_superseded=False). Für Abwärtskompatibilität."""
    return load_filtered(agent_id, filter_project=filter_project, active_project=active_project)


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


def _apply_write(
    data: MemoryStore,
    key: str,
    content: str,
    *,
    expires_at: str | None = None,
    confidence: float | None = None,
    project: str | None = None,
    check_contradictions: bool = True,
) -> tuple[MemoryEntry, list[str]]:
    """Mutiert `data` in-place: schreibt einen Eintrag, gibt (entry, superseded) zurück.

    Pure Mutation ohne File-IO — wird von write_key (Single) und
    write_keys_bulk (Batch) genutzt um N Read+Write zu vermeiden.
    """
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
    return data[key], superseded_keys


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
    entry, superseded_keys = _apply_write(
        data, key, content,
        expires_at=expires_at,
        confidence=confidence,
        project=project,
        check_contradictions=check_contradictions,
    )
    save(agent_id, data)
    return entry, superseded_keys


def write_keys_bulk(
    agent_id: str,
    entries: list[dict],
) -> list[tuple[MemoryEntry, list[str]]]:
    """Schreibt mehrere Memory-Einträge mit einem File-Read+Write-Pass.

    entries: Liste von Dicts mit Keys `key`, `content` (Pflicht) und
    optional `expires_at`, `confidence`, `project`, `check_contradictions`.

    Returns: Liste von (entry, superseded_keys), Reihenfolge wie entries.
    Bei leerer Liste: kein File-Write, leere Liste zurück.
    """
    if not entries:
        return []
    data = load(agent_id)
    results: list[tuple[MemoryEntry, list[str]]] = []
    for e in entries:
        results.append(_apply_write(
            data,
            e["key"],
            e["content"],
            expires_at=e.get("expires_at"),
            confidence=e.get("confidence"),
            project=e.get("project"),
            check_contradictions=e.get("check_contradictions", True),
        ))
    save(agent_id, data)
    return results


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
