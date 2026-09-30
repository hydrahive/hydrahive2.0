#!/usr/bin/env python3
"""Erzeugt core/src/hydrahive/skills/system_defaults/_history.json.

Für jeden mitgelieferten System-Skill: SHA-256 aller Fassungen aus der
Git-Geschichte (inkl. Umbenennungen) plus der aktuellen Datei. Der Loader
aktualisiert eine Live-Datei nur, wenn sie einer dieser Fassungen entspricht
(docs/specs/system-skills-update.md). Nach jeder Änderung an einem System-Skill
laufen lassen, sonst schlägt test_system_skills_update fehl.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "core" / "src" / "hydrahive" / "skills" / "system_defaults"


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def _versions(rel: str) -> list[str]:
    """SHA-256 aller Fassungen (älteste zuerst), über Umbenennungen hinweg."""
    log = _git("log", "--follow", "--format=%H", "--name-only", "--", rel)
    shas: list[str] = []
    lines = [ln for ln in log.splitlines() if ln.strip()]
    for commit, path in zip(lines[0::2], lines[1::2]):
        try:
            blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
                                  check=True, capture_output=True).stdout
        except subprocess.CalledProcessError:
            continue  # Datei in diesem Commit gelöscht
        sha = hashlib.sha256(blob).hexdigest()
        if sha not in shas:
            shas.append(sha)
    return list(reversed(shas))


def main() -> int:
    history: dict[str, list[str]] = {}
    for f in sorted(DEFAULTS.glob("*.md")):
        rel = str(f.relative_to(ROOT))
        shas = _versions(rel)
        current = hashlib.sha256(f.read_bytes()).hexdigest()
        if current not in shas:
            shas.append(current)
        history[f.name] = shas
    out = DEFAULTS / "_history.json"
    out.write_text(json.dumps(history, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: {len(history)} Skills, {sum(len(v) for v in history.values())} Fassungen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
