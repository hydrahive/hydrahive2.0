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
_CONFIDENCE_STEP = 0.1  # Reinforcement-Schritt: neue_conf = old + STEP * (1 - old)


# ---------------------------------------------------------------------------
# Internes
# ---------------------------------------------------------------------------

def _memory_file(agent_id: str) -> Path:
    return settings.agents_dir / agent_id / "memory.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _migrate_entry(value: Any) -> MemoryEntry:
    """Migriert alte String-Werte und #50-Einträge (ohne Confidence) zum aktuellen Schema."""
    if isinstance(value, str):
        return {
            "content": value,
            "created_at": None,
            "updated_at": None,
            "expires_at": None,
            "confidence": _CONFIDENCE_DEFAULT,
            "reinforcements": 0,
            "last_reinforced_at": None,
        }
    if isinstance(value, dict):
        # #50-Einträge: Confidence-Felder ergänzen falls nicht vorhanden
        entry = value.copy()
        entry.setdefault("confidence", _CONFIDENCE_DEFAULT)
        entry.setdefault("reinforcements", 0)
        entry.setdefault("last_reinforced_at", None)
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


def load_active(agent_id: str) -> MemoryStore:
    """Wie load(), aber ohne abgelaufene Einträge. Für Iteration ohne _is_expired-Import."""
    data = load(agent_id)
    return {k: v for k, v in data.items() if not _is_expired(v)}


def save(agent_id: str, data: MemoryStore) -> None:
    path = _memory_file(agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_entry(agent_id: str, key: str) -> MemoryEntry | None:
    """
    Gibt den vollständigen MemoryEntry zurück, oder None wenn nicht vorhanden / abgelaufen.
    Für Aufrufer die Metadaten (created_at, confidence, expires_at, ...) benötigen.
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
) -> MemoryEntry:
    """
    Schreibt einen Memory-Eintrag. Gibt den gespeicherten Entry zurück.

    expires_at: ISO-Timestamp oder relative Angabe (+2h, +1d, +7d, +4w).
    confidence: Initiale Confidence für neue Einträge (0.0–1.0, default 0.5).
                Bei bestehenden Einträgen wird confidence per Reinforcement erhöht
                und dieser Parameter ignoriert.

    Update-Verhalten bei bestehendem Eintrag:
    - content und updated_at werden immer überschrieben.
    - confidence wird per Reinforcement-Formel erhöht (konvergiert gegen 1.0).
    - expires_at wird NUR aktualisiert wenn explizit übergeben —
      bestehender Ablaufzeitpunkt bleibt sonst erhalten.
    """
    data = load(agent_id)
    now = _now_iso()
    parsed_expiry = _parse_expiry(expires_at) if expires_at else None

    existing = data.get(key)
    if existing and isinstance(existing, dict):
        old_conf = existing.get("confidence", _CONFIDENCE_DEFAULT)
        existing["content"] = content
        existing["updated_at"] = now
        existing["confidence"] = _reinforce_confidence(old_conf)
        existing["reinforcements"] = existing.get("reinforcements", 0) + 1
        existing["last_reinforced_at"] = now
        if parsed_expiry is not None:
            existing["expires_at"] = parsed_expiry
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
        }

    save(agent_id, data)
    return data[key]


def delete_key(agent_id: str, key: str) -> bool:
    data = load(agent_id)
    if key not in data:
        return False
    del data[key]
    save(agent_id, data)
    return True


def list_keys(agent_id: str) -> list[str]:
    """Gibt alle nicht-abgelaufenen Keys zurück."""
    data = load(agent_id)
    return sorted(k for k, v in data.items() if not _is_expired(v))


def cleanup_expired(agent_id: str) -> int:
    """
    Löscht alle abgelaufenen Einträge aus der Memory-Datei.
    Gibt die Anzahl der gelöschten Einträge zurück.
    """
    data = load(agent_id)
    expired_keys = [k for k, v in data.items() if _is_expired(v)]
    if not expired_keys:
        return 0
    for k in expired_keys:
        del data[k]
    save(agent_id, data)
    return len(expired_keys)
