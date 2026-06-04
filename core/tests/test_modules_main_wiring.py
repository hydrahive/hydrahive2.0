"""Task 6 — mount_module_routers: Routers aus dem REGISTRY in eine FastAPI-App einbauen."""
from __future__ import annotations

import sys
from pathlib import Path

# core/tests/ liegt wegen __init__.py nicht automatisch im sys.path; einfügen
# damit test_module_loader direkt importierbar ist (Task-5-Helper-Wiederverwendung).
sys.path.insert(0, str(Path(__file__).parent))


def test_mount_module_routers(mod_env):
    from test_module_loader import _make_module  # reuse Task 5 helper
    _make_module(mod_env / "modules", "alpha")
    from fastapi import FastAPI
    from hydrahive.modules.loader import load_all
    from hydrahive.api.main import mount_module_routers
    load_all()
    test_app = FastAPI()
    mount_module_routers(test_app)
    paths = {r.path for r in test_app.routes if hasattr(r, "path")}
    assert "/api/modules/alpha/ping" in paths
