"""Memory v2 — Public Facade.

Re-exportiert die API aus _memory_model (pure Logic) und _memory_io
(File-IO + Read/Write). Dieses Modul hält alle Symbole stabil für
externe Importer.
"""
from __future__ import annotations

from hydrahive.tools._memory_io import (
    cleanup_expired,
    delete_key,
    list_keys,
    load,
    load_active,
    load_filtered,
    read_entry,
    read_key,
    save,
    write_key,
    write_keys_bulk,
    _memory_file,
)
from hydrahive.tools._memory_model import (
    MemoryEntry,
    MemoryStore,
    _CONFIDENCE_DEFAULT,
    _CONFIDENCE_STEP,
    _CONTRADICTION_THRESHOLD,
    _is_expired,
    _jaccard_similarity,
    _migrate_entry,
    _now_iso,
    _parse_expiry,
    _project_matches,
    _reinforce_confidence,
    find_contradictions,
    is_expired,
    mark_superseded,
)

__all__ = [
    # Typen
    "MemoryEntry",
    "MemoryStore",
    # File-IO + Read/Write
    "cleanup_expired",
    "delete_key",
    "list_keys",
    "load",
    "load_active",
    "load_filtered",
    "read_entry",
    "read_key",
    "save",
    "write_key",
    "write_keys_bulk",
    # Pure Logic (public)
    "find_contradictions",
    "is_expired",
    "mark_superseded",
]
