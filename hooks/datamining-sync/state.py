"""Pro-CC-Session Sidecar-State: hh_session_id + Sync-Offset. Atomarer Write."""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT = {"hh_session_id": None, "synced": 0}


def _path(state_dir: Path, cc_session_id: str) -> Path:
    return state_dir / f"{cc_session_id}.json"


def load_state(state_dir: Path, cc_session_id: str) -> dict:
    p = _path(state_dir, cc_session_id)
    if not p.exists():
        return dict(_DEFAULT)
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)
    return {"hh_session_id": data.get("hh_session_id"), "synced": int(data.get("synced", 0))}


def save_state(state_dir: Path, cc_session_id: str, hh_session_id: str, synced: int) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _path(state_dir, cc_session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"hh_session_id": hh_session_id, "synced": synced}))
    tmp.replace(p)
