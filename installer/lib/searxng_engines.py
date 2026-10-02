#!/usr/bin/env python3
"""Bing und Yandex in einer SearXNG-Einstellungsdatei einschalten (idempotent).

Aufruf: searxng_engines.py <settings.yml>
Ausgabe: "changed" oder "unchanged"; Exit 1 bei unlesbarer/ungültiger Datei
(dann wird nichts geschrieben).

Hintergrund (02.10.2026): DuckDuckGo/Startpage zeigten CAPTCHAs, Brave meldete
„zu viele Anfragen“, Google blieb leer — die Websuche lieferte 0 Treffer.
Bing und Yandex funktionierten, waren aber aus. Spec:
docs/specs/websearch-blocked-engines.md §7.

Regeln:
- Nur fehlende Einträge ergänzen ({name, disabled: false}); hat der Nutzer einen
  der beiden selbst eingetragen (auch disabled: true), bleibt er wie er ist.
- Alle anderen Abschnitte und Anbieter bleiben erhalten.
- Ist nichts zu tun, wird die Datei nicht angefasst (Kommentare bleiben).
- Läuft mit dem Python des SearXNG-venv (dort ist PyYAML installiert).
"""
from __future__ import annotations

import os
import sys
import tempfile

import yaml

WANTED = ("bing", "yandex")


def merge(settings: dict) -> bool:
    """Ergänzt fehlende Anbieter in-place. True, wenn sich etwas geändert hat."""
    engines = settings.get("engines")
    if engines is None:
        engines = []
    if not isinstance(engines, list):
        raise TypeError("engines ist keine Liste")
    present = {e.get("name") for e in engines if isinstance(e, dict)}
    missing = [name for name in WANTED if name not in present]
    if not missing:
        return False
    engines.extend({"name": name, "disabled": False} for name in missing)
    settings["engines"] = engines
    return True


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            settings = yaml.safe_load(fh)
        if not isinstance(settings, dict):
            raise TypeError("keine YAML-Zuordnung")
        changed = merge(settings)
    except (OSError, yaml.YAMLError, TypeError) as exc:
        sys.stderr.write(f"searxng_engines: {path} nicht verarbeitet: {exc}\n")
        return 1
    if not changed:
        sys.stdout.write("unchanged\n")
        return 0
    # Atomar schreiben: erst Nachbardatei, dann umbenennen (Rechte übernehmen).
    directory = os.path.dirname(os.path.abspath(path))
    mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".settings-", suffix=".yml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            yaml.safe_dump(settings, out, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except OSError as exc:
        if os.path.exists(tmp):
            os.unlink(tmp)
        sys.stderr.write(f"searxng_engines: schreiben fehlgeschlagen: {exc}\n")
        return 1
    sys.stdout.write("changed\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("Aufruf: searxng_engines.py <settings.yml>\n")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
