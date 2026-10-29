"""Task 3c82a8d5 (Plan docs/plans/themes-entfernen.md, Teil B): Das Layout-Theme-System ist
auch im Backend entfernt – kein Theme-Installer, kein Theme-Hub, keine /api/themes-Routen."""
from __future__ import annotations

import importlib.util


def test_theme_paket_ist_weg():
    assert importlib.util.find_spec("hydrahive.themes") is None
    assert importlib.util.find_spec("hydrahive.api.routes.themes") is None


def test_keine_theme_routen_in_der_api():
    from hydrahive.api.main import app

    pfade = [getattr(r, "path", "") for r in app.routes]
    # die Routen lagen unter /api/admin/themes – jede API-Route mit Segment „themes“ ist ein Rest
    assert [p for p in pfade if p.startswith("/api/") and "/themes" in p] == []


def test_keine_theme_einstellungen_mehr():
    from hydrahive.settings import settings

    for name in ("themes_frontend_dir", "theme_hub_cache", "theme_hub_git_url", "theme_hub_extra_git_urls"):
        assert not hasattr(type(settings), name), name
