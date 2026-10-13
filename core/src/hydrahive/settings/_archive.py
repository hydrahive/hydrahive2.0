"""Einstellungen des System-Archivs (docs/specs/archiv-system.md, Etappe 2).

Nur Stellschrauben mit sicheren Standards. Der Ort des Archivs steht nicht hier,
sondern in archive/location.py (nur über die Admin-Konsole).
"""
from __future__ import annotations

import os
from functools import cached_property


def _number(env: str, default: float, *, low: float, high: float) -> float:
    """Zahl aus der ENV. Ungültig oder außerhalb [low, high] → Standard."""
    try:
        value = float(os.environ.get(env, default))
    except ValueError:
        return default
    return value if low <= value <= high else default


class _ArchiveMixin:
    @cached_property
    def archive_compress_level(self) -> int:
        """gzip-Stufe beim Packen. Gemessen (13.10.): 400 MB in 5 s (1) gegen 60 s (9) bei 12 % mehr Platz."""
        return int(_number("HH_ARCHIVE_COMPRESS_LEVEL", 1, low=1, high=9))

    @cached_property
    def archive_preview_budget_s(self) -> float:
        """So lange darf die Lösch-Vorschau höchstens Bytes zählen, danach „mindestens X“."""
        return _number("HH_ARCHIVE_PREVIEW_BUDGET_S", 5.0, low=0.1, high=120.0)

    @cached_property
    def archive_space_reserve(self) -> float:
        """Platz-Prüfung vor dem Packen: frei ≥ Größe × (1 + Reserve)."""
        return _number("HH_ARCHIVE_SPACE_RESERVE", 0.05, low=0.0, high=1.0)

    @cached_property
    def archive_jobs_keep(self) -> int:
        """So viele fertige Lösch-Aufträge zeigt „Laufende Vorgänge“."""
        return int(_number("HH_ARCHIVE_JOBS_KEEP", 20, low=1, high=500))
