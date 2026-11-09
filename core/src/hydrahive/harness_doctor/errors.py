"""Häufigste Tool-Fehlerursachen für den Harness Doctor (Task 2123ef7e, Harness-Kurs L01/L11).

Gleiche Ursachen werden zusammengefasst, indem Pfade, URLs, IDs und Zahlen maskiert werden. Nur die erste Zeile
einer Meldung zählt. Tracebacks, Freitext aus Spezialisten-Ausgaben und rohes Provider-JSON werden abgeschnitten.

Status: `error` ist ein echter Fehler. `pending` heißt unbeendet: Der Aufruf läuft noch oder wurde bei einem
Dienstneustart abgebrochen. `cancelled` heißt, der Nutzer hat gestoppt. Beides wird getrennt gezählt und nicht
als Tool-Fehler gewertet.
"""
from __future__ import annotations

import re
from collections import Counter

_MAX_CAUSE_CHARS = 140
_UUID = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.IGNORECASE)
_HEX_ID = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
# Pfad = absolut (/… oder ~/… am Wortanfang), oder mindestens zwei Trenner, oder Datei mit Endung.
# So bleiben Wortpaare wie „speech/tts“ lesbar, echte Pfade werden vollständig maskiert (inkl. Bindestrichen,
# damit keine Teile von Dateinamen übrig bleiben). Pfade werden VOR IDs ersetzt, sonst zerschneiden IDs sie.
_PATH = re.compile(
    r"(?:(?<![\w.@/-])~?/[\w.@-]*[\w@-](?:/[\w.@-]*[\w@-])*)"
    r"|(?:[\w.@-]+/){2,}[\w.@-]+"
    r"|(?:[\w.@-]+/)+[\w@-]+\.[A-Za-z0-9]{1,6}\b"
)
_NUMBER = re.compile(r"\d+")
_LIST = re.compile(r"\[[^\]]*(?:\]|$)")
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
# Nach diesem Präfix folgt Freitext aus der Ausgabe eines Spezialisten – nur die Art bleibt stehen.
_SPECIALIST_TEXT = re.compile(r"^(Specialist-Status \w+: \w+:).*$")


def _strip_content(first: str) -> str:
    """Entfernt Inhalte, die nicht ins Cockpit gehören: URLs, Spezialisten-Freitext, rohes JSON."""
    first = _URL.sub("<url>", first)
    first = _SPECIALIST_TEXT.sub(r"\1 …", first)
    if "{" in first:
        first = first.split("{", 1)[0].rstrip() + " …"
    return first


def normalize(message: str | None) -> str:
    if not message or not message.strip():
        return "(ohne Fehlermeldung)"
    first = _strip_content(message.strip().splitlines()[0])
    first = _LIST.sub("[…]", first)
    first = _PATH.sub("<pfad>", first)
    first = _UUID.sub("<id>", first)
    first = _HEX_ID.sub("<id>", first)
    first = _NUMBER.sub("<n>", first)
    first = re.sub(r"\s+", " ", first).strip()
    return first[:_MAX_CAUSE_CHARS]


def cluster_errors(rows: list[dict], *, limit: int = 10) -> dict:
    counts: Counter[tuple[str, str]] = Counter()
    interrupted = cancelled = 0
    for row in rows:
        status = row.get("status")
        amount = int(row.get("amount") or 1)   # SQL liefert vorgruppierte Zeilen mit Anzahl
        if status == "pending":
            interrupted += amount
        elif status == "cancelled":
            cancelled += amount
        elif status == "error":
            counts[(row.get("tool_name") or "?", normalize(row.get("error_message")))] += amount
    total = sum(counts.values())
    clusters = [
        {"tool": tool, "cause": cause, "count": count, "share": round(count / total, 2)}
        for (tool, cause), count in counts.most_common(limit)
    ]
    return {"errors_total": total, "interrupted": interrupted, "cancelled": cancelled, "clusters": clusters}
