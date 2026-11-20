"""Ketten-Anker: Zielbild und Originalauftrag reisen unverändert durch jede Ebene.

Befund 20.11.2026 (Till: „stille Post“): Buddy → Projekt-Agent → Spezialist,
jede Ebene schrieb den Auftrag neu. Der Backend-Spezialist bekam 6 Kernpunkte
nicht, der Frontend-Spezialist kein Wort zum Ziel. Ergebnis: grüne Tests gegen
das falsche Ziel.

Lösung im Code, nicht im Prompt (Till: „Scripting statt Prompting“):
- Der ERSTE Auftrag einer Kette bekommt zwei Blöcke angehängt: das Zieldokument
  (wenn angegeben) und den Originalauftrag, je mit SHA-256-Prüfsumme.
- Jede weitere Ebene (ask_agent im Handoff-Lauf) holt die Blöcke aus dem
  Auftrag, den der eigene Lauf bekommen hat, und hängt sie UNVERÄNDERT an –
  egal was der Agent selbst schreibt. Fehlt ein Block oder passt die Prüfsumme
  nicht, wird er aus der Quelle wiederhergestellt.
- Felder in AgentLink gehen nicht: der Server speichert nur feste Felder
  (/opt/hydralink/agentlink/backend/main.py, AgentState). Darum stehen die
  Blöcke mit festen Markern im Auftragstext selbst.

docs/specs/chain-anchor.md
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_BLOCK_CHARS = 60_000   # Schutz gegen versehentlich riesige Dateien
_KINDS = ("ziel", "original")
_BLOCK_RE = re.compile(
    r"<!--hh-(?P<kind>ziel|original) sha=(?P<sha>[0-9a-f]{64})(?: quelle=(?P<src>[^>\n]{0,300}))?-->\n"
    r"(?P<body>.*?)\n<!--/hh-(?P=kind)-->",
    re.S,
)
_HEADINGS = {
    "ziel": "## Zieldokument (verbindlich, unverändert vom Kern angehängt)",
    "original": "## Originalauftrag (unverändert vom Kern angehängt)",
}


@dataclass(frozen=True)
class Block:
    kind: str
    body: str
    source: str = ""

    @property
    def sha(self) -> str:
        return digest(self.body)

    def render(self) -> str:
        src = f" quelle={self.source}" if self.source else ""
        return f"{_HEADINGS[self.kind]}\n<!--hh-{self.kind} sha={self.sha}{src}-->\n{self.body}\n<!--/hh-{self.kind}-->"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract(text: str) -> dict[str, Block]:
    """Gültige Blöcke aus einem Auftragstext. Ein Block mit falscher Prüfsumme gilt als nicht vorhanden."""
    found: dict[str, Block] = {}
    for m in _BLOCK_RE.finditer(text or ""):
        body = m.group("body")
        if digest(body) == m.group("sha") and m.group("kind") not in found:
            found[m.group("kind")] = Block(m.group("kind"), body, (m.group("src") or "").strip())
    return found


def strip(text: str) -> str:
    """Auftragstext ohne Anker-Blöcke (auch beschädigte), damit nichts doppelt oder verfälscht mitreist."""
    out = text or ""
    for kind in _KINDS:
        out = out.replace(_HEADINGS[kind], "")
    out = re.sub(r"<!--hh-(ziel|original) sha=[^>]*-->\n.*?\n<!--/hh-\1-->", "", out, flags=re.S)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def compose(task_text: str, inherited: dict[str, Block], *, ziel: Block | None = None) -> str:
    """Endgültiger Auftragstext: eigener Text + Anker-Blöcke (geerbt hat Vorrang, sonst neu).

    - Geerbte Blöcke (aus dem eigenen eingehenden Auftrag) werden immer übernommen;
      der Agent kann sie weder weglassen noch ersetzen.
    - Ohne geerbten Original-Block ist dieser Auftrag der Ursprung: sein eigener
      Text wird zum Originalauftrag.
    - Ein neues Zieldokument zählt nur, wenn kein Ziel geerbt ist.
    """
    own = strip(task_text)
    blocks: list[Block] = []
    z = inherited.get("ziel") or ziel
    if z is not None:
        blocks.append(z)
    blocks.append(inherited.get("original") or Block("original", own))
    return "\n\n".join([own] + [b.render() for b in blocks])
