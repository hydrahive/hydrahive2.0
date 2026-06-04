"""Gemeinsame Test-Fixtures und Hilfsfunktionen für alle HydraHive2-Tests."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response


# ---------------------------------------------------------------------------
# FastAPI-Fehlerformat
# Alle API-Fehler haben die Form: {"detail": {"code": "...", "params": {}}}
# Zugriff: error_code(response) == "invalid_credentials"
# ---------------------------------------------------------------------------

def error_code(response: Response) -> str:
    """Gibt den code-String aus einer FastAPI-Fehlerantwort zurück."""
    return response.json()["detail"]["code"]


def error_params(response: Response) -> dict:
    """Gibt die params aus einer FastAPI-Fehlerantwort zurück."""
    return response.json()["detail"].get("params", {})


# ---------------------------------------------------------------------------
# Auth-Hilfsfunktion
# ---------------------------------------------------------------------------

def bearer(token: str) -> dict:
    """Gibt einen Authorization-Header zurück."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# API-Integration-Test-Setup
# Session-scoped autouse: legt einmalig Tmp-Dir + Test-User + Test-Agent an,
# setzt HH_*-Env-Vars. Andere Tests (memory/crystallize/etc.) nutzen eigene
# tmp_path + monkeypatch — die Env-Vars stören dort nicht weil das Modul
# settings cached_property nutzt und seine Pfade selbst per monkeypatch
# überschrieben werden.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment with temporary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        os.environ["HH_DATA_DIR"] = str(tmp_path / "data")
        os.environ["HH_CONFIG_DIR"] = str(tmp_path / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""

        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)

        users_file = tmp_path / "config" / "users.json"
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        users = {
            "testuser": {"password_hash": password_hash, "role": "user"},
            "admin": {"password_hash": password_hash, "role": "admin"},
        }
        users_file.write_text(json.dumps(users, indent=2))

        agent_id = "test-agent-001"
        agent_dir = tmp_path / "data" / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        agent_config = {
            "id": agent_id,
            "name": "Test Agent",
            "type": "master",
            "owner": "admin",
            "llm_model": "claude-3-7-sonnet-20250219",
            "tools": [],
            "temperature": 0.7,
            "max_tokens": 4096,
            "thinking_budget": 10000,
            "created_at": "2026-01-01T00:00:00Z",
        }
        (agent_dir / "config.json").write_text(json.dumps(agent_config, indent=2))

        yield tmp_path


@pytest.fixture
def client(setup_test_env):
    """FastAPI TestClient with mocked lifespan to avoid full startup."""
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
    """Returns valid auth headers with JWT token for testuser."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _akte_db(request, setup_test_env):
    """Migrierte DB + leere akte_*-Tabellen für Patientenakte-Tests.

    Diese Tests gehen direkt über db() (nicht über die client-Fixture) und
    brauchen daher init_db() im Test-Env. Muster wie test_ega._ensure_db.
    No-op für alle anderen Tests.
    """
    if "test_akte_" not in request.node.nodeid:
        yield
        return
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.patientenakte.schema import ENTITIES

    init_db()
    with db() as conn:
        for spec in ENTITIES.values():
            conn.execute(f"DELETE FROM {spec.table}")
        conn.execute("DELETE FROM akte_patient")
    yield


@pytest.fixture
def admin_headers(client):
    """Returns valid auth headers with JWT token for admin."""
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "testpass123",
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_module():
    """Factory: legt ein Fake-Modul-Verzeichnis (manifest + migration + backend) an."""
    def _make(modules_dir: Path, mid: str) -> Path:
        md = modules_dir / mid
        (md / "backend").mkdir(parents=True)
        (md / "migrations").mkdir()
        (md / "manifest.json").write_text('{"id":"%s","name":"X","version":"1.0.0"}' % mid)
        (md / "migrations" / "001_t.sql").write_text(f"CREATE TABLE module_{mid}_t (id INTEGER);")
        (md / "backend" / "__init__.py").write_text(
            "from fastapi import APIRouter\n"
            "def register(ctx):\n"
            "    r=APIRouter()\n"
            "    @r.get('/ping')\n"
            "    def ping(): return {'ok': True}\n"
            "    ctx.register_router(r)\n"
            "    ctx.register_migrations('migrations')\n"
        )
        return md
    return _make


@pytest.fixture
def mod_env(tmp_path, monkeypatch):
    """Isolierte Modul-Umgebung: frische DB + repointete Modul-Pfade.

    Umgeht den session-weiten settings-Freeze (cached_property): das autouse
    `setup_test_env` friert die Pfade einmalig ein, `monkeypatch.setenv` ist
    danach wirkungslos. Muster wie test_research_apis.py — direkt per setattr.
    `db()`/`init_db()` lesen `settings.sessions_db` pro Aufruf, daher landet die
    DB im tmp_path.
    """
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "test.db", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    monkeypatch.setattr(settings, "modules_dir", tmp_path / "modules", raising=False)
    monkeypatch.setattr(settings, "base_dir", tmp_path / "repo", raising=False)
    monkeypatch.setattr(settings, "module_hub_cache", tmp_path / "hub", raising=False)
    (tmp_path / "data").mkdir()
    (tmp_path / "modules").mkdir()
    from hydrahive.db import init_db
    init_db()
    return tmp_path


