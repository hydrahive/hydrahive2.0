#!/usr/bin/env python3
"""Findet feste Text-Modellnamen in Modulen (Plan E5, Spec agent-templates.md Kap. 3.2).

Module sollen eine Rolle (Agenten-Template) anfragen statt eines festen Modells. Ausnahme pro Zeile mit
Kommentar `# feste-modell-id: Grund`. Tests (`*/tests/*`) sind ausgenommen.

Aufruf: python3 scripts/check_fixed_models.py [Ordner …]   (Standard: modules/)
Exit 1 bei Treffern ohne Begründung.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    r"""(?:llm_model|model)\s*=\s*["'](?:claude-|openai-codex/|gpt-|MiniMax-|gemini-|anthropic/|openai/gpt)""")
ALLOW = "feste-modell-id:"


def scan(roots: list[Path]) -> list[str]:
    hits = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.parts or "node_modules" in path.parts:
                continue
            for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if PATTERN.search(line) and ALLOW not in line:
                    hits.append(f"{path}:{n}: {line.strip()}")
    return hits


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or [Path("modules")]
    hits = scan([r for r in roots if r.is_dir()])
    for h in hits:
        print(h)
    if hits:
        print(f"\n{len(hits)} feste Modellnamen ohne Begründung. Rolle anfragen: complete(..., template=\"modul-schnell\")"
              f" oder Zeile mit '# {ALLOW} Grund' markieren.")
        return 1
    print("Keine festen Modellnamen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
