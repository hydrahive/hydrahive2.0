"""Abnahme per Skript (Ketten-Anker Etappe 3, docs/specs/chain-anchor.md).

Befund 20.11.2026: Fertig-Meldungen waren Nacherzählungen ohne Bezug zum Ziel.
Jetzt gilt: Ein Auftrag mit Abnahme-Block ist erst „fertig“, wenn der Bericht
für JEDEN Punkt eine Tabellenzeile `| ID | ✅ | Beleg |` enthält. Fehlt ein
Punkt, steht ❌/unklar oder fehlt der Beleg, setzt der Kern den Status auf
„incomplete“. Das Skript prüft Form und Vollständigkeit; ob der Beleg stimmt,
prüft weiterhin der Auftraggeber (es ersetzt keine Gegenprobe).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_ID = r"[A-Z]{1,3}\d{1,3}"
_ZIEL_ROW = re.compile(rf"^\|\s*\**(?P<id>{_ID})\**\s*\|")
_ZIEL_BULLET = re.compile(rf"^[-*]\s+\**(?P<id>{_ID})\**[\s:.)]")
_REPORT_ROW = re.compile(rf"^\s*\|\s*\**(?P<id>{_ID})\**\s*\|(?P<stand>[^|\n]*)\|(?P<beleg>[^|\n]*)\|")
_EMPTY_BELEG = {"", "-", "—", "–", "…", "...", "n/a", "tbd", "?"}


def points_from_ziel(ziel: str) -> dict[str, str]:
    """Abnahme-Punkte eines Zieldokuments: ID → Originalzeile (Tabelle `| A1 | …` oder Liste `- P1 …`)."""
    out: dict[str, str] = {}
    for line in (ziel or "").splitlines():
        s = line.strip()
        m = _ZIEL_ROW.match(s) or _ZIEL_BULLET.match(s)
        if m and m.group("id") not in out:
            out[m.group("id")] = s
    return out


def body_for(points: dict[str, str], ids: list[str]) -> str:
    """Inhalt des Abnahme-Blocks: die gewählten Punkte wörtlich, in der Reihenfolge des Zieldokuments."""
    return "\n".join(points[i] for i in points if i in ids)


def ids_in(body: str) -> list[str]:
    return list(points_from_ziel(body))


@dataclass
class Verdict:
    required: list[str]
    ok: list[str] = field(default_factory=list)
    open: list[str] = field(default_factory=list)          # ❌ oder Stand unklar
    no_evidence: list[str] = field(default_factory=list)   # ✅ ohne Beleg
    missing: list[str] = field(default_factory=list)       # keine Zeile im Bericht

    @property
    def complete(self) -> bool:
        return bool(self.required) and len(self.ok) == len(self.required)

    def render(self) -> str:
        head = ("Kern-Abnahmeprüfung: ALLE Punkte ✅ mit Beleg." if self.complete else
                "Kern-Abnahmeprüfung: UNVOLLSTÄNDIG – Status „incomplete“, nicht fertig.")
        rows = [f"- {i}: " + ("✅ mit Beleg" if i in self.ok else "❌ nicht erfüllt / unklar" if i in self.open
                              else "✅ ohne Beleg" if i in self.no_evidence else "fehlt im Bericht")
                for i in self.required]
        return "\n".join([head, *rows])


def check_report(abnahme_body: str, report: str) -> Verdict:
    """Bericht gegen die Abnahme-Punkte prüfen. Maßgeblich ist die LETZTE Zeile je Punkt."""
    v = Verdict(required=ids_in(abnahme_body))
    rows: dict[str, tuple[str, str]] = {}
    for line in (report or "").splitlines():
        m = _REPORT_ROW.match(line)
        if m:
            rows[m.group("id")] = (m.group("stand").strip(), m.group("beleg").strip())
    for pid in v.required:
        if pid not in rows:
            v.missing.append(pid)
            continue
        stand, beleg = rows[pid]
        if "✅" not in stand or "❌" in stand:
            v.open.append(pid)
        elif beleg.strip("`*_ ").lower() in _EMPTY_BELEG:
            v.no_evidence.append(pid)
        else:
            v.ok.append(pid)
    return v
