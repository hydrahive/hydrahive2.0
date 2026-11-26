"""Hybrid-Suche im Katalog (Spec S7): Wortsuche immer, Kosinus wenn ein Vektor da ist, zusammengeführt per RRF.

Wichtig: gefiltert wird VOR dem Rang auf ``allowed``. Ein gesperrtes Tool wird weder bewertet noch geliefert, es gibt also
kein Leck von Name, Beschreibung oder Schema (Spec S7).
"""
from __future__ import annotations

import math
import re
from collections import Counter

from hydrahive.catalog.index import CatalogEntry

_TOKEN = re.compile(r"[a-zäöüß0-9]+")
_STOP = frozenset({"der", "die", "das", "den", "dem", "ein", "eine", "einen", "und", "oder", "zu", "zum", "zur", "im", "in",
                   "ist", "mit", "von", "für", "auf", "an", "ich", "mir", "mal", "bitte", "the", "a", "of", "to", "and"})
RRF_K = 60
_STEM = 5            # Wortanfang: „erzeugen“ ↔ „erzeugt“, „schicken“ ↔ „schickt“, „lesen“ ↔ „liest“ (grob, aber ohne Abhängigkeit)


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


def _stems(text: str) -> list[str]:
    return [t[:_STEM] for t in tokens(text)]


def _expand(query_tokens: list[str], vocab: set[str]) -> list[str]:
    """Anfrage-Wörter plus Bestandteile deutscher Komposita („Webseite“ → „seite“), soweit der Katalog sie kennt."""
    terms = [t[:_STEM] for t in query_tokens]
    for t in query_tokens:
        if len(t) >= 8:
            terms += [w[:_STEM] for w in vocab if len(w) >= _STEM and w != t and w[:_STEM] in t]
    return list(dict.fromkeys(terms))


def bm25_rank(query: str, entries: list[CatalogEntry]) -> list[CatalogEntry]:
    """BM25-Wortsuche über Wortanfänge (Titel doppelt gewichtet); Treffer auch in Komposita. Ohne Treffer: leere Liste."""
    qt = tokens(query)
    if not qt or not entries:
        return []
    doc_tokens = [tokens(f"{e.name.replace('_', ' ')} {e.title} {e.title} {e.text}") for e in entries]
    vocab = {w for d in doc_tokens for w in d}
    q = _expand(qt, vocab)
    docs = [Counter(t[:_STEM] for t in d) for d in doc_tokens]
    # Teiltreffer in Komposita („Websuche“ enthält „suche“): zählt, aber schwächer als ein Wortanfang
    subs = [Counter(w for w in d if len(w) > _STEM) for d in doc_tokens]
    lens = [len(d) or 1 for d in doc_tokens]
    avg = sum(lens) / len(lens)
    n = len(docs)
    scored: list[tuple[float, int]] = []
    for i, d in enumerate(docs):
        score = 0.0
        for term in q:
            tf = d.get(term, 0) + 0.5 * sum(c for w, c in subs[i].items() if not w.startswith(term) and term in w)
            if not tf:
                continue
            df = sum(1 for j, x in enumerate(docs) if term in x or any(term in w for w in subs[j]))
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * lens[i] / avg))
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda s: (-s[0], entries[s[1]].name))          # stabil bei gleichem Rang
    return [entries[i] for _, i in scored]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def vector_rank(query_vector: list[float], entries: list[CatalogEntry], vectors: dict[str, list[float]]) -> list[CatalogEntry]:
    scored = [(_cosine(query_vector, vectors[e.name]), e) for e in entries if e.name in vectors]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: (-s[0], s[1].name))
    return [e for _, e in scored]


def rrf(rankings: list[list[CatalogEntry]], limit: int) -> list[CatalogEntry]:
    """Reciprocal Rank Fusion: Summe 1/(k+Rang) über alle Ranglisten."""
    score: dict[str, float] = {}
    by_name: dict[str, CatalogEntry] = {}
    for ranking in rankings:
        for pos, e in enumerate(ranking):
            score[e.name] = score.get(e.name, 0.0) + 1.0 / (RRF_K + pos + 1)
            by_name[e.name] = e
    order = sorted(score, key=lambda n: (-score[n], n))
    return [by_name[n] for n in order[:limit]]


def search(query: str, *, allowed: set[str], kind: str = "tool", limit: int = 5,
           query_vector: list[float] | None = None) -> list[CatalogEntry]:
    """Treffer für ``query`` innerhalb von ``allowed``. Filtert vor dem Rang (kein Leck gesperrter Tools)."""
    from hydrahive.catalog import _store
    store = _store.get_store()
    candidates = [e for e in store.entries() if e.kind == kind and e.name in allowed]   # ZUERST filtern
    if not candidates:
        return []
    rankings = [bm25_rank(query, candidates)]
    if query_vector is not None:
        rankings.append(vector_rank(query_vector, candidates, store.vectors()))
    return rrf([r for r in rankings if r], limit)
