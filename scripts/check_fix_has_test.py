#!/usr/bin/env python3
"""Fix-Test-Guard: ein Fix-PR mit Produktivcode bringt einen Test mit (docs/specs/fix-test-guard.md, Kurs L10).

Aufruf in CI:  python3 scripts/check_fix_has_test.py <base-sha> <head-sha>
PR-Titel, -Beschreibung und Branch kommen NUR über Umgebungsvariablen (PR_TITLE, PR_BODY, PR_BRANCH), nie über die
Kommandozeile – Schutz vor Script-Injection über PR-Texte. Modus über FIX_TEST_GUARD_MODE: warn (Default) | block.
Das Skript liest nur Git-Daten und schreibt nur nach stdout.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# Fix = Präfix wie in Commit-Konventionen: „fix:“, „fix(scope):“, „fix “ – nicht „Fix-Test-Guard“ oder „Fixtures“.
_FIX = re.compile(r"^\s*(fix|hotfix|bugfix)(\(|:|\s|$)", re.IGNORECASE)
_PROD_EXT = re.compile(r"\.(py|ts|tsx|sh|mjs|js)$")
# Ordner tests/ bzw. test/, oder Dateiname test_*.py, *_test.py, *.test.ts(x), *.spec.ts(x).
# Nur der Dateiname zählt – „check_fix_has_test.py“ endet auf „_test.py“, ist aber kein Test.
_TEST_FILE = re.compile(r"(^|/)(tests?/.+|test_[^/]+\.py|[^/]+\.(test|spec)\.tsx?)$")
_EXEMPTION = re.compile(r"^\s*Kein Test:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_MIN_REASON = 10


@dataclass
class Result:
    is_fix: bool
    prod_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    exemption: str | None = None

    @property
    def violation(self) -> bool:
        return self.is_fix and bool(self.prod_files) and not self.test_files and self.exemption is None

    @property
    def ok(self) -> bool:
        return not self.violation


def _exemption(body: str) -> str | None:
    match = _EXEMPTION.search(body or "")
    if match and len(match.group(1)) >= _MIN_REASON:
        return match.group(1)
    return None


def evaluate(files: list[str], *, title: str, subjects: list[str], body: str, branch: str) -> Result:
    branch_name = (branch or "").split("/", 1)[0] if "/" in (branch or "") else (branch or "")
    is_fix = any(_FIX.match(text or "") for text in [title, branch_name, *subjects])
    tests = sorted(f for f in files if _TEST_FILE.search(f))
    prod = sorted(f for f in files if _PROD_EXT.search(f) and f not in tests)
    return Result(is_fix=is_fix, prod_files=prod, test_files=tests, exemption=_exemption(body))


def message(result: Result) -> str:
    if not result.is_fix:
        return "Kein Fix-PR – Regel greift nicht."
    if result.test_files:
        return f"Fix mit Test: {len(result.test_files)} Testdatei(en) geändert."
    if result.exemption:
        return f"Fix ohne Test, begründet: {result.exemption}"
    if not result.prod_files:
        return "Fix ohne Produktivcode – Regel greift nicht."
    shown = ", ".join(result.prod_files[:5]) + (" …" if len(result.prod_files) > 5 else "")
    return (
        f"Fix ohne Test: {len(result.prod_files)} Produktivdatei(en) geändert ({shown}), keine Testdatei.\n"
        "WARUM: Ein Fix ohne Test kann unbemerkt wiederkommen (Kurs L10, Regel docs/specs/fix-test-guard.md).\n"
        "BEHEBEN: Test ergänzen, der ohne den Fix rot ist (test_*.py, *.test.ts …),\n"
        "         oder in die PR-Beschreibung schreiben: „Kein Test: <Begründung>“."
    )


def exit_code(result: Result, mode: str) -> int:
    return 1 if result.violation and (mode or "").strip().lower() == "block" else 0


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stdout.write("Aufruf: check_fix_has_test.py <base-sha> <head-sha>\n")
        return 2
    base, head = argv[1], argv[2]
    files = [f for f in _git("diff", "--name-only", f"{base}...{head}").splitlines() if f.strip()]
    subjects = [s for s in _git("log", "--format=%s", f"{base}..{head}").splitlines() if s.strip()]
    result = evaluate(files, title=os.environ.get("PR_TITLE", ""), subjects=subjects,
                      body=os.environ.get("PR_BODY", ""), branch=os.environ.get("PR_BRANCH", ""))
    mode = os.environ.get("FIX_TEST_GUARD_MODE", "warn")
    text = message(result)
    if result.violation:
        first, _, rest = text.partition("\n")
        level = "error" if exit_code(result, mode) else "warning"
        sys.stdout.write(f"::{level} title=Fix-Test-Guard::{first}\n")
        sys.stdout.write(rest + "\n")
    else:
        sys.stdout.write(text + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### Fix-Test-Guard ({mode})\n\n```\n{text}\n```\n")
    return exit_code(result, mode)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
