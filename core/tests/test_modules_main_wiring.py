"""Task 6 — mount_module_routers: Routers aus dem REGISTRY in eine FastAPI-App einbauen."""
from __future__ import annotations


def test_mount_module_routers(mod_env, make_module):
    make_module(mod_env / "modules", "alpha")
    from fastapi import FastAPI
    from hydrahive.modules.loader import load_all
    from hydrahive.api.main import mount_module_routers
    load_all()
    test_app = FastAPI()
    mount_module_routers(test_app)
    paths = {r.path for r in test_app.routes if hasattr(r, "path")}
    assert "/api/modules/alpha/ping" in paths
