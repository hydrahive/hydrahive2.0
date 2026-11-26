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

    def set_vector(self, name: str, vector: list[float], *, for_entry: CatalogEntry | None = None) -> None:
        """Vektor speichern – mit ``for_entry`` nur, wenn der Eintrag inzwischen nicht ersetzt wurde (Review #783: Race
        zwischen Hintergrund-Embedding und replace_all ließ sonst einen veralteten Vektor stehen)."""
        with self._lock:
            current = self._entries.get(name)
            if current is None or (for_entry is not None and current != for_entry):
                return
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


_SYNC_LOCK = None


async def sync_embeddings(store: MemoryStore, *, pool=None, model: str) -> int:
    """Vektoren für Einträge ohne Vektor nachholen (im Speicher). Liefert die Anzahl neuer Vektoren.

    Ohne Modell: 0, ohne Fehler (Wortsuche, K9). ``pool`` wird nicht gebraucht (Vektoren liegen im Speicher, keine
    Postgres-Tabelle – Review #783); der Parameter bleibt für Aufrufer. Gebündelt per ``aembed_batch``, ein Lauf
    gleichzeitig. Fehler werden geschluckt und geloggt; die Suche läuft unabhängig davon weiter.
    """
    global _SYNC_LOCK
    import asyncio
    if not model:
        return 0
    if _SYNC_LOCK is None:
        _SYNC_LOCK = asyncio.Lock()
    if _SYNC_LOCK.locked():
        return 0                                           # läuft schon – nicht doppelt
    async with _SYNC_LOCK:
        try:
            from hydrahive.llm.embed import aembed_batch
        except Exception:  # noqa: BLE001
            logger.debug("Katalog-Embeddings: Modul nicht verfügbar", exc_info=True)
            return 0
        done = 0
        missing = store.missing_vectors()
        for start in range(0, len(missing), 32):
            chunk = missing[start:start + 32]
            try:
                vecs = await aembed_batch([f"{e.name}: {e.text}"[:4000] for e in chunk], model, embed_type="db")
            except Exception:  # noqa: BLE001
                logger.debug("Katalog-Embeddings: Batch fehlgeschlagen", exc_info=True)
                continue
            for entry, vec in zip(chunk, vecs or []):
                if vec:
                    store.set_vector(entry.name, vec, for_entry=entry)
                    done += 1
        return done
