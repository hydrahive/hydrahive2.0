#!/usr/bin/env python3
"""Hilfe-Guard: eine nutzersichtbare Änderung bringt ihren Hilfe-Artikel mit (docs/specs/hilfe-guard.md).

Aufruf in CI:  python3 scripts/check_help_updated.py <base-sha> <head-sha>
Die PR-Beschreibung kommt NUR über die Umgebungsvariable PR_BODY, nie über die Kommandozeile – Schutz vor
Script-Injection über PR-Texte. Modus über HILFE_GUARD_MODE: warn (Default) | block.
Das Skript liest nur Git-Daten und Dateien des Checkouts und schreibt nur nach stdout (und in die Step-Summary).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HELP_DIR = "frontend/src/i18n/help/de"

# Nutzersichtbar (Spec §2, Kern). Tests (*.test.*, tests/) zählen nicht – das wird in _is_test geprüft.
_VISIBLE = (
    re.compile(r"^frontend/src/features/.+\.tsx$"),
    re.compile(r"^frontend/src/shared/.+\.tsx$"),
    re.compile(r"^frontend/src/i18n/locales/de/[^/]+\.json$"),
    re.compile(r"^installer/update[^/]*\.sh$"),
    re.compile(r"^installer/lib/update-[^/]*\.sh$"),
    re.compile(r"^installer/install[^/]*\.sh$"),
)
_TEST = re.compile(r"(^|/)(tests?/.+|[^/]+\.(test|spec)\.[^/]+)$")
_HELP_FILE = re.compile(r"^" + re.escape(HELP_DIR) + r"/[^/]+\.md$")
_FEATURE = re.compile(r"^frontend/src/features/([^/]+)/")
_LOCALE = re.compile(r"^frontend/src/i18n/locales/de/([^/]+)\.json$")
_TOPIC = re.compile(r"""\btopic=["']([a-z0-9_-]+)["']""")
# Eigene Zeile; [ \t] statt \s, damit der Grund nicht aus der Folgezeile geholt wird.
_EXEMPTION = re.compile(r"^[ \t]*Keine Hilfe nötig:[ \t]*(.*?)[ \t]*$", re.IGNORECASE | re.MULTILINE)
_PLACEHOLDER = "<Begründung>"      # Platzhalter aus der Fehlermeldung zählt nicht als Begründung
_MIN_REASON = 10
_SHOWN = 5
_GENERAL = f"passenden Artikel unter {HELP_DIR}/ wählen oder neu anlegen"


@dataclass
class Result:
    visible_files: list[str] = field(default_factory=list)
    help_files: list[str] = field(default_factory=list)
    exemption: str | None = None
    suggestions: list[str] = field(default_factory=list)

    @property
    def violation(self) -> bool:
        return bool(self.visible_files) and not self.help_files and self.exemption is None

    @property
    def ok(self) -> bool:
        return not self.violation


def _exemption(body: str | None) -> str | None:
    for match in _EXEMPTION.finditer(body or ""):
        reason = match.group(1)
        if len(reason) >= _MIN_REASON and reason != _PLACEHOLDER:
            return reason
    return None


def _is_visible(path: str) -> bool:
    return not _TEST.search(path) and any(p.search(path) for p in _VISIBLE)


def _topics_in_folder(root: Path, folder: str) -> set[str]:
    topics: set[str] = set()
    base = root / "frontend" / "src" / "features" / folder
    if not base.is_dir():
        return topics
    for tsx in base.rglob("*.tsx"):
        rel = tsx.relative_to(root).as_posix()
        if _TEST.search(rel):
            continue
        try:
            topics.update(_TOPIC.findall(tsx.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return topics


def _suggest(visible: list[str], root: Path | None) -> list[str]:
    """Artikel-Vorschlag: Ordner unter features/ → topic aus den HelpButton-Stellen (nur existierende Artikel)."""
    if root is None:
        return []
    found: set[str] = set()
    for path in visible:
        candidates: set[str] = set()
        feature = _FEATURE.match(path)
        locale = _LOCALE.match(path)
        if feature:
            candidates = _topics_in_folder(root, feature.group(1)) or {feature.group(1)}
        elif locale:
            candidates = {locale.group(1)}
        found.update(c for c in candidates if _TOPIC.fullmatch(f'topic="{c}"') and (root / HELP_DIR / f"{c}.md").is_file())
    return [f"{HELP_DIR}/{name}.md" for name in sorted(found)]


def evaluate(files: list[str], *, body: str | None, root: Path | None = None) -> Result:
    visible = sorted(f for f in files if _is_visible(f))
    helps = sorted(f for f in files if _HELP_FILE.match(f))
    result = Result(visible_files=visible, help_files=helps, exemption=_exemption(body))
    if result.violation:
        result.suggestions = _suggest(visible, root)
    return result


def message(result: Result) -> str:
    if not result.visible_files:
        return "Keine nutzersichtbare Änderung – Regel greift nicht."
    if result.help_files:
        return f"Hilfe geändert: {len(result.help_files)} Hilfe-Datei(en) zur nutzersichtbaren Änderung."
    if result.exemption:
        return f"Nutzersichtbar ohne Hilfe, begründet: {result.exemption}"
    shown = ", ".join(result.visible_files[:_SHOWN]) + (" …" if len(result.visible_files) > _SHOWN else "")
    target = " oder ".join(result.suggestions) + " ergänzen" if result.suggestions else _GENERAL
    return (
        f"Hilfe fehlt: {len(result.visible_files)} nutzersichtbare Datei(en) geändert ({shown}), keine Hilfe-Datei.\n"
        "WARUM: Wiki und PDF-Handbuch entstehen aus den Hilfe-Artikeln – ohne Artikel-Änderung bleibt das Handbuch alt\n"
        "       (Regel docs/specs/hilfe-guard.md).\n"
        f"BEHEBEN: {target}\n"
        "         oder in die PR-Beschreibung schreiben: „Keine Hilfe nötig: <Begründung>“."
    )


def exit_code(result: Result, mode: str) -> int:
    return 1 if result.violation and (mode or "").strip().lower() == "block" else 0


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stdout.write("Aufruf: check_help_updated.py <base-sha> <head-sha>\n")
        return 2
    base, head = argv[1], argv[2]
    files = [f for f in _git("diff", "--name-only", f"{base}...{head}").splitlines() if f.strip()]
    root = Path(_git("rev-parse", "--show-toplevel").strip())
    result = evaluate(files, body=os.environ.get("PR_BODY", ""), root=root)
    mode = os.environ.get("HILFE_GUARD_MODE", "warn")
    text = message(result)
    if result.violation:
        first, _, rest = text.partition("\n")
        level = "error" if exit_code(result, mode) else "warning"
        sys.stdout.write(f"::{level} title=Hilfe-Guard::{first}\n")
        sys.stdout.write(rest + "\n")
    else:
        sys.stdout.write(text + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Hilfe-Guard ({mode})\n\n```\n{text}\n```\n")
    return exit_code(result, mode)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
