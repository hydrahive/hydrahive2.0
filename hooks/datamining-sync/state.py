"""Pro-CC-Session Sidecar-State: hh_session_id + Menge bereits gesendeter
Message-IDs. Atomarer Write.

ID-Set statt Zähler: robust gegen Umordnung/Einschübe im Transkript — eine in
der Mitte eingefügte Message wird gesendet, eine bereits gesehene nie erneut
(ein reiner Offset-Zähler würde die neue überspringen).
"""
from __future__ import annotations

import json
from pathlib import Path


def _path(state_dir: Path, cc_session_id: str) -> Path:
    return state_dir / f"{cc_session_id}.json"


def load_state(state_dir: Path, cc_session_id: str) -> dict:
    p = _path(state_dir, cc_session_id)
    if not p.exists():
        return {"hh_session_id": None, "synced_ids": []}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {"hh_session_id": None, "synced_ids": []}
    ids = data.get("synced_ids")
    return {
        "hh_session_id": data.get("hh_session_id"),
        "synced_ids": list(ids) if isinstance(ids, list) else [],
    }


def save_state(state_dir: Path, cc_session_id: str, hh_session_id: str,
               synced_ids: list[str]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _path(state_dir, cc_session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"hh_session_id": hh_session_id, "synced_ids": synced_ids}))
    tmp.replace(p)
