"""Self-contained Test-Fixtures für das Patientenakte-Modul.

Eigenständig (kein Core-conftest), damit die Tests im Hub-Repo ohne den
HydraHive-Core-Testbaum laufen. Hängt den Modul-Router an die App, weil der
Core ihn nach dem Port nicht mehr selbst einbindet.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Modul-Verzeichnis auf den Pfad: `from backend import ...` (Paket mit relativen Imports)
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_DATA_DIR"] = str(tmp_path / "data")
        os.environ["HH_CONFIG_DIR"] = str(tmp_path / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": password_hash, "role": "user"},
            "admin": {"password_hash": password_hash, "role": "admin"},
        }, indent=2))

        # Modul-Router an die Core-App hängen (Core bindet sie nach dem Port nicht ein).
        from hydrahive.api import main
        from backend import router as akte_router
        from backend.fhir_routes import router as fhir_router
        from backend.ega_routes import router as ega_router
        # Exakt wie der Core (mount_module_routers): jeder Router unter /api/modules/<id>.
        # Damit treffen die Tests denselben Pfad wie die Produktion.
        mod_prefix = "/api/modules/patientenakte"
        main.app.include_router(akte_router, prefix=mod_prefix)
        main.app.include_router(fhir_router, prefix=mod_prefix)
        main.app.include_router(ega_router, prefix=mod_prefix)

        yield tmp_path


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from hydrahive.db import init_db
    init_db()

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    from hydrahive.api import main
    original_lifespan = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.router.lifespan_context = original_lifespan


@pytest.fixture
def auth_headers(client):
    r = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _akte_db(setup_test_env):
    """Migrierte DB + leere akte_*-Tabellen vor jedem Test."""
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from backend.schema import ENTITIES

    init_db()
    with db() as conn:
        for spec in ENTITIES.values():
            conn.execute(f"DELETE FROM {spec.table}")
        conn.execute("DELETE FROM akte_patient")
        # Import-Stores ebenfalls leeren → Test-Isolation unabhängig von Reihenfolge
        conn.execute("DELETE FROM fhir_resources")
        conn.execute("DELETE FROM ega_records")
    yield
