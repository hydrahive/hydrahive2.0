"""Atomic Read-Modify-Write für llm.json — verhindert Token-Refresh-Races.

Mehrere Prozesse (API-Server, Web-UI, CLI) können gleichzeitig OAuth-Token
refreshen. Ohne Synchronisation überschreibt der eine den anderen, oder
mischen die Felder eines partiellen Writes mit einem fertigen Block.

Strategie:
  1. fcntl.flock auf Sidecar-Lock-File (.lock)
  2. read llm.json frisch (jemand könnte gerade davor geschrieben haben)
  3. Provider-Block in-memory mutieren
  4. Atomic write (temp + rename) — kein partieller Read auf Reader-Seite

Lock ist exklusiv und blockierend: bei sehr vielen parallelen Refreshes
serialisiert er sie. Praktisch passiert max. 1 Refresh pro 5min pro
Provider, also ist die Wartezeit vernachlässigbar.
"""
from __future__ import annotations

import fcntl
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def update_provider_oauth(
    path: Path,
    provider_id: str,
    new_oauth_block: dict[str, Any],
) -> None:
    """Aktualisiert den oauth-Block eines Providers in llm.json atomar.

    Hält einen flock auf <path>.lock während Read+Write. Wenn der Provider
    nicht existiert: kein Write, nur Warning-Log (kann passieren wenn die
    Config zwischen Lookup und Refresh manuell geändert wurde).
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock_fd:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        try:
            if not path.exists():
                logger.warning("update_provider_oauth: %s existiert nicht", path)
                return
            data = json.loads(path.read_text())
            for p in data.get("providers", []):
                if p.get("id") == provider_id:
                    p["oauth"] = new_oauth_block
                    _atomic_write(path, data)
                    return
            logger.warning(
                "update_provider_oauth: provider '%s' nicht in %s", provider_id, path,
            )
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
