"""Audit: bereits geleakte Secrets in sessions.db aufspüren (und bereinigen).

Hintergrund: Ein Agent hat einen Provider-Key in den Tool-Output gedumpt; der
landete im Klartext in messages.content / tool_calls.result. Die Redaction-
Engstelle (credentials.redaction, dispatcher) verhindert das künftig — aber
Alt-Einträge sind nicht betroffen. Dieses Script sucht nach Key-FORMEN (nicht
Werten, da rotierte Keys nicht mehr in der Config stehen) und meldet Fundorte
maskiert. Mit --redact werden die Treffer in der DB durch [REDACTED] ersetzt.

Aufruf (auf dem Server, gegen die echte sessions.db):
    python -m hydrahive.scripts.audit_leaked_secrets            # dry-run, nur Report
    python -m hydrahive.scripts.audit_leaked_secrets --redact   # Treffer bereinigen
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from hydrahive.credentials.redaction import detect_secrets, mask, redact_detected
from hydrahive.db.connection import db
from hydrahive.settings import settings


@dataclass(frozen=True)
class Hit:
    source: str  # "messages" | "tool_calls" | "observations"
    row_id: str
    session_id: str | None
    masked: tuple[str, ...]


def _scan(conn, source: str, text_col: str) -> list[Hit]:
    hits: list[Hit] = []
    rows = conn.execute(
        f"SELECT id, session_id, {text_col} AS text FROM {source} WHERE {text_col} IS NOT NULL"
    ).fetchall()
    for row in rows:
        found = detect_secrets(row["text"])
        if found:
            hits.append(Hit(source, row["id"], row["session_id"],
                            tuple(mask(s) for s in dict.fromkeys(found))))
    return hits


def _observation_files() -> list:
    base = settings.agents_dir
    if not base.exists():
        return []
    return sorted(base.glob("*/observations/*.jsonl"))


def _scan_observations() -> list[Hit]:
    """Observations liegen on-disk (agents/<id>/observations/<session>.jsonl),
    nicht in der DB — eigener Scan, sonst Audit-Lücke."""
    hits: list[Hit] = []
    for path in _observation_files():
        found: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            found.extend(detect_secrets(line))
        if found:
            session_id = path.stem
            hits.append(Hit("observations", str(path), session_id,
                            tuple(mask(s) for s in dict.fromkeys(found))))
    return hits


def find_hits() -> list[Hit]:
    """Alle Fundorte in messages.content + tool_calls.result + Observation-JSONLs."""
    with db() as conn:
        db_hits = _scan(conn, "messages", "content") + _scan(conn, "tool_calls", "result")
    return db_hits + _scan_observations()


def redact_hits() -> int:
    """Ersetzt secret-förmige Substrings durch [REDACTED]. Gibt #betroffene Zeilen/Dateien."""
    affected = 0
    with db() as conn:
        for source, text_col in (("messages", "content"), ("tool_calls", "result")):
            rows = conn.execute(
                f"SELECT id, {text_col} AS text FROM {source} WHERE {text_col} IS NOT NULL"
            ).fetchall()
            for row in rows:
                if not detect_secrets(row["text"]):
                    continue
                cleaned = redact_detected(row["text"])
                conn.execute(f"UPDATE {source} SET {text_col} = ? WHERE id = ?", (cleaned, row["id"]))
                affected += 1

    for path in _observation_files():
        original = path.read_text(encoding="utf-8")
        if not detect_secrets(original):
            continue
        cleaned = "\n".join(redact_detected(line) for line in original.splitlines())
        if original.endswith("\n"):
            cleaned += "\n"
        tmp = path.with_suffix(".jsonl.tmp")
        tmp.write_text(cleaned, encoding="utf-8")
        tmp.replace(path)
        affected += 1

    return affected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Geleakte Secrets in sessions.db aufspüren.")
    parser.add_argument("--redact", action="store_true",
                        help="Treffer in der DB durch [REDACTED] ersetzen (sonst nur Report).")
    args = parser.parse_args(argv)

    hits = find_hits()
    if not hits:
        print("✓ Keine secret-förmigen Strings in messages/tool_calls gefunden.")
        return 0

    print(f"⚠ {len(hits)} Zeile(n) mit secret-förmigen Strings:\n")
    for hit in hits:
        print(f"  [{hit.source}] id={hit.row_id} session={hit.session_id}")
        for m in hit.masked:
            print(f"      → {m}")

    if not args.redact:
        print(f"\nDry-Run. Zum Bereinigen: python -m {__spec__.name} --redact")
        return 0

    affected = redact_hits()
    print(f"\n✓ {affected} Zeile(n) bereinigt — Secrets durch [REDACTED] ersetzt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
