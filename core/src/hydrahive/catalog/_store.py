"""Speicher des Katalogs: im Speicher (immer) plus optional Postgres für Vektoren (Spec K9, Plan Aufgabe 3).

Der Speicher-Store ist die Wahrheit für Einträge und Wortsuche und läuft ohne Postgres und ohne Embedding-Modell.
Vektoren kommen später und nie blockierend dazu (``sync_embeddings``); fehlt Pool oder Modell, bleibt es bei der Wortsuche.
"""
from __future__ import annotations

import logging
import threading

from hydrahive.catalog.index import CatalogEntry

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, CatalogEntry] = {}
        self._vectors: dict[str, list[float]] = {}

    def entries(self) -> list[CatalogEntry]:
        with self._lock:
            return list(self._entries.values())

    def vectors(self) -> dict[str, list[float]]:
        with self._lock:
            return dict(self._vectors)

    def replace_all(self, entries: list[CatalogEntry], *, kind: str) -> None:
        """Ersetzt alle Einträge der Art ``kind``; Einträge, die es nicht mehr gibt, verschwinden samt Vektor."""
        with self._lock:
            keep = {n: e for n, e in self._entries.items() if e.kind != kind}
            fresh = {e.name: e for e in entries}
            changed = {n for n, e in fresh.items() if self._entries.get(n) != e}
            self._entries = {**keep, **fresh}
            for name in list(self._vectors):
                if name not in self._entries or name in changed:
                    self._vectors.pop(name, None)           # veraltet oder weg → Vektor neu berechnen

    def set_vector(self, name: str, vector: list[float]) -> None:
        with self._lock:
            if name in self._entries:
                self._vectors[name] = list(vector)

    def missing_vectors(self) -> list[CatalogEntry]:
        with self._lock:
            return [e for n, e in self._entries.items() if n not in self._vectors]


_STORE: MemoryStore | None = None
_LOCK = threading.Lock()


def get_store() -> MemoryStore:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = MemoryStore()
        return _STORE


def reset_store() -> None:
    global _STORE
    with _LOCK:
        _STORE = None


async def sync_embeddings(store: MemoryStore, *, pool, model: str) -> int:
    """Vektoren für Einträge ohne Vektor nachholen. Liefert die Anzahl neuer Vektoren.

    Ohne Pool oder Modell: 0, ohne Fehler (Wortsuche, K9). Fehler (Pool, Modell, Netz) werden geschluckt und geloggt; die
    Suche läuft unabhängig davon weiter. Postgres-Persistenz folgt in ``_pg`` (siehe unten), nie im Anfragepfad.
    """
    if pool is None or not model:
        return 0
    try:
        async with pool.acquire():
            pass
        from hydrahive.llm.embed import aembed
    except Exception:  # noqa: BLE001 — nie blockieren, nie kippen
        logger.debug("Katalog-Embeddings: Pool/Modell nicht verfügbar", exc_info=True)
        return 0
    done = 0
    for entry in store.missing_vectors():
        try:
            vec = await aembed(f"{entry.name}: {entry.text}"[:4000], model)
        except Exception:  # noqa: BLE001
            logger.debug("Katalog-Embedding für %s fehlgeschlagen", entry.name, exc_info=True)
            continue
        if vec:
            store.set_vector(entry.name, vec)
            done += 1
    return done
