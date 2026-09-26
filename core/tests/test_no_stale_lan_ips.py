"""Keine Adressen aus dem abgeschalteten 192.168.3.x-Netz im Repo.

Hintergrund: Nach dem Netzwerkumzug (192.168.3.x -> 192.168.178.x, Mai/Juni
2026) standen die alten Adressen noch in Beispielen, README-Befehlen und
Platzhaltern. Wer danach etwas einrichtete, kopierte sie in echte
Konfiguration — der MCP-Server, Gitea, Webmin und die Extension-URLs zeigten
monatelang auf 192.168.3.21/.22, die es nicht mehr gibt.

Beispiele sollen 127.0.0.1 (lokaler Dienst) oder eine reservierte Test-
Domain (*.example.test) verwenden, keine echte LAN-Adresse.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STALE = re.compile(r"192\.168\.3\.\d{1,3}")
SKIP_DIRS = {".git", "node_modules", "dist", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
SUFFIXES = {".py", ".ts", ".tsx", ".json", ".md", ".sh", ".yml", ".yaml", ".toml", ".ini", ".conf", ".service"}


def _files():
    for path in REPO.rglob("*"):
        if path.is_file() and path.suffix in SUFFIXES and not SKIP_DIRS.intersection(path.parts):
            yield path


def test_no_addresses_from_retired_192_168_3_network():
    hits = []
    for path in _files():
        if path == Path(__file__):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if STALE.search(line):
                hits.append(f"{path.relative_to(REPO)}:{lineno}: {line.strip()[:100]}")

    assert not hits, (
        "Adressen aus dem abgeschalteten 192.168.3.x-Netz gefunden. "
        "Für Beispiele 127.0.0.1 oder *.example.test verwenden:\n" + "\n".join(hits)
    )
