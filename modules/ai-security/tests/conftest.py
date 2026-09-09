"""Isolierte Fixtures für das AI-Security-Modul."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        os.environ["HH_DATA_DIR"] = str(root / "data")
        os.environ["HH_CONFIG_DIR"] = str(root / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        os.environ["HH_AI_SECURITY_AIG_URL"] = "http://127.0.0.1:8088"
        os.environ["HH_AI_SECURITY_TARGETS"] = "http://127.0.0.1:11434"
        (root / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (root / "config" / "users.json").write_text(json.dumps({
            "alice": {"password_hash": password_hash, "role": "user"},
            "bob": {"password_hash": password_hash, "role": "user"},
        }))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("ai-security", MODULE_DIR / "migrations")

        from hydrahive.api import main
        from backend.routes import router
        main.app.include_router(router, prefix="/api/modules/ai-security")
        yield root


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
    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.router.lifespan_context = original


@pytest.fixture
def alice(client):
    response = client.post("/api/auth/login", json={"username": "alice", "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def bob(client):
    response = client.post("/api/auth/login", json={"username": "bob", "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def clean_scans():
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    init_db()
    with db() as conn:
        conn.execute("DELETE FROM module_ai_security_scans")
    yield
