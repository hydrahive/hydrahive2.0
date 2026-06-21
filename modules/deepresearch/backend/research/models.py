"""Datenmodelle für den Research-Loop (in-memory; Persistenz als JSON in service.py)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    """Ein extrahiertes Ergebnis aus einer Quell-Seite."""
    url: str
    title: str
    summary: str
    evidence: str = ""
    image: str = ""  # OG-Image der Quelle (für den späteren HTML-Report)


@dataclass
class RunState:
    """Veränderlicher Zustand eines Research-Laufs."""
    question: str
    model: str | None = None
    category: str = "general"
    subquestions: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    report_md: str = ""
    round: int = 0
    queries_used: set[str] = field(default_factory=set)
    urls_seen: set[str] = field(default_factory=set)

    def sources(self) -> list[dict]:
        """Deduplizierte Quellenliste {url, title, image} in Fund-Reihenfolge."""
        seen: set[str] = set()
        out: list[dict] = []
        for f in self.findings:
            if f.url in seen:
                continue
            seen.add(f.url)
            out.append({"url": f.url, "title": f.title, "image": f.image})
        return out
