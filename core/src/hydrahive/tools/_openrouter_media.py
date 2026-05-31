"""Geteilte Helfer für OpenRouter-Media-Tools (Bild, Musik, Audio …).

Key-Lookup + base64→Datei-Speicherung an EINER Stelle — kein Duplikat über die
einzelnen Tool-Module. Die Datei muss in einem servable-Verzeichnis landen
(Aufrufer übergibt ctx.workspace/… → von /api/files ausgeliefert).
"""
from __future__ import annotations

import uuid
from pathlib import Path


def openrouter_key() -> str:
    from hydrahive.llm._config import get_provider_key, load_config
    return get_provider_key(load_config(), "openrouter")


def save_bytes(raw: bytes, dest_dir: Path, ext: str) -> Path:
    """Schreibt raw bytes als <uuid>.<ext> in dest_dir (wird angelegt)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{uuid.uuid4().hex}.{ext.lstrip('.')}"
    path.write_bytes(raw)
    return path
