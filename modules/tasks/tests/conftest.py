"""Self-contained Test-Fixtures für das Tasks-Modul."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
    isolated_root,
    only_own_files,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
    remove_test_tree,
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "alice": {"password_hash": pw_hash, "role": "user"},
            "bob":   {"password_hash": pw_hash, "role": "user"},
        }, indent=2))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("tasks", MODULE_DIR / "migrations")

        from hydrahive.api import main
        from backend.routes import router as tasks_router
        main.app.include_router(tasks_router, prefix="/api/modules/tasks")

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
    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig


@pytest.fixture
def alice(client):
    r = client.post("/api/auth/login", json={"username": "alice", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def bob(client):
    r = client.post("/api/auth/login", json={"username": "bob", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def clean_tasks():
    from hydrahive.db import init_db
    init_db()
    with only_own_rows("module_tasks"):
        yield
