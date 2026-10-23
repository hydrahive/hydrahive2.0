"""Handbuch für den Hilfe-Assistenten (docs/plans/help-assistant.md): laden und nach Wörtern durchsuchen.

Quellen sind dieselben Dateien wie im Cockpit: die Hilfe-Artikel frontend/src/i18n/help/<lang>/<topic>.md und das
Benutzerhandbuch docs/USER_GUIDE.md (Topic „guide“). Das Repo liegt auf jeder Installation komplett vor.
Sprache wie loadHelp() im Frontend: Sprache des Nutzers, sonst Deutsch, sonst Englisch.
Wortsuche statt Embeddings: ~190 KB Text, und sie funktioniert auch ohne Embedding-Modell.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
GUIDE_TOPIC = "guide"
EXCERPT_CHARS = 400
_TOPIC = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_LANG = re.compile(r"^[a-z]{2}$")
_FALLBACK = ("de", "en")


def _help_dir() -> Path:
    return REPO_ROOT / "frontend" / "src" / "i18n" / "help"


def _guide() -> Path:
    return REPO_ROOT / "docs" / "USER_GUIDE.md"


def _langs(lang: str) -> list[str]:
    code = (lang or "").split("-")[0].lower()
    first = [code] if _LANG.match(code) else []
    return first + [lg for lg in _FALLBACK if lg not in first]


def clear_cache() -> None:
    _load.cache_clear()
    _sections.cache_clear()


@lru_cache(maxsize=256)
def _load(topic: str, lang: str) -> str | None:
    if topic == GUIDE_TOPIC:
        p = _guide()
        return p.read_text(encoding="utf-8") if p.is_file() else None
    for lg in _langs(lang):
        p = _help_dir() / lg / f"{topic}.md"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None


def topics(lang: str = "de") -> list[str]:
    """Alle Topics (Artikel in irgendeiner Sprache + Handbuch), sortiert."""
    names: set[str] = set()
    base = _help_dir()
    if base.is_dir():
        for lang_dir in base.iterdir():
            if lang_dir.is_dir():
                names.update(p.stem for p in lang_dir.glob("*.md") if _TOPIC.match(p.stem))
    if _guide().is_file():
        names.add(GUIDE_TOPIC)
    return sorted(names)


def read(topic: str, lang: str = "de") -> str | None:
    """Text eines Artikels oder None. Nur bekannte Topic-Namen – nie einen Pfad aus dem Modell durchreichen."""
    if not isinstance(topic, str) or not _TOPIC.match(topic) or topic not in topics(lang):
        return None
    return _load(topic, lang)


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _words(query: str) -> list[str]:
    return [w for w in re.findall(r"\w+", _norm(query)) if len(w) > 1]


@lru_cache(maxsize=8)
def _sections(lang: str) -> tuple[tuple[str, str, str], ...]:
    """(topic, Überschrift, Text) je Abschnitt aller Artikel."""
    out: list[tuple[str, str, str]] = []
    for topic in topics(lang):
        text = _load(topic, lang) or ""
        heading, buf = topic, []
        for line in text.splitlines():
            m = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
            if m:
                if buf:
                    out.append((topic, heading, "\n".join(buf).strip()))
                heading, buf = m.group(1), []
            else:
                buf.append(line)
        if buf:
            out.append((topic, heading, "\n".join(buf).strip()))
    return tuple(out)


def search(query: str, lang: str = "de", limit: int = 6) -> list[dict]:
    """Abschnitte, in denen die Suchwörter vorkommen – die mit den meisten verschiedenen Wörtern zuerst,
    Treffer in der Überschrift zählen doppelt."""
    words = _words(query)
    if not words:
        return []
    scored: list[tuple[int, int, dict]] = []
    for i, (topic, heading, body) in enumerate(_sections(lang)):
        h, b = _norm(heading), _norm(body)
        found = [w for w in words if w in h or w in b]
        if not found:
            continue
        score = len(found) * 10 + sum(1 for w in found if w in h) * 10 + min(sum(b.count(w) for w in found), 9)
        excerpt = re.sub(r"\s+", " ", body)[:EXCERPT_CHARS]
        scored.append((-score, i, {"topic": topic, "heading": heading, "excerpt": excerpt}))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [hit for _, _, hit in scored[:max(1, limit)]]
