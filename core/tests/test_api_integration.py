"""FastAPI Integration Tests für Auth- und Sessions-API.

Diese Tests verwenden FastAPI TestClient und eine temporäre SQLite-DB.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Test-Setup: Überschreibe Settings bevor App geladen wird
@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment with temporary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Override Settings via Environment
        os.environ["HH_DATA_DIR"] = str(tmp_path / "data")
        os.environ["HH_CONFIG_DIR"] = str(tmp_path / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        
        # Create directories
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        
        # Create test user
        users_file = tmp_path / "config" / "users.json"
        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        users = {
            "testuser": {"password_hash": password_hash, "role": "user"},
            "admin": {"password_hash": password_hash, "role": "admin"},
        }
        users_file.write_text(json.dumps(users, indent=2))
        
        # Create test agent
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
    
    # Initialize DB
    init_db()
    
    # Create minimal app without full lifespan
    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        # Minimal startup - nur DB, keine Services
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield
    
    # Import and override app
    from hydrahive.api import main
    original_lifespan = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    
    with TestClient(main.app) as test_client:
        yield test_client
    
    # Restore
    main.app.router.lifespan_context = original_lifespan


@pytest.fixture
def auth_headers(client):
    """Returns valid auth headers with JWT token for testuser."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    """Returns valid auth headers with JWT token for admin."""
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Auth Tests
# ============================================================================

def test_login_success(client):
    """POST /api/auth/login mit gültigem User → 200 + access_token."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "testuser"
    assert data["role"] == "user"


def test_login_wrong_password(client):
    """POST /api/auth/login mit falschem Passwort → 401."""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_me_without_token(client):
    """GET /api/auth/me ohne Token → 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    """GET /api/auth/me mit gültigem Token → 200 + username/role."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "user"


# ============================================================================
# Sessions Tests
# ============================================================================

def test_sessions_without_token(client):
    """GET /api/sessions ohne Token → 401."""
    response = client.get("/api/sessions")
    assert response.status_code == 401


def test_sessions_with_token_empty(client, auth_headers):
    """GET /api/sessions mit Token → 200 + Liste (ggf. leer)."""
    response = client.get("/api/sessions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_session_success(client, auth_headers):
    """POST /api/sessions mit gültigem Agent → 201 + Session-Objekt."""
    response = client.post("/api/sessions", headers=auth_headers, json={
        "agent_id": "test-agent-001",
        "title": "Test Session"
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["agent_id"] == "test-agent-001"
    assert data["user_id"] == "testuser"
    assert data["title"] == "Test Session"
    assert data["status"] == "active"


def test_get_foreign_session_as_user_403(client, auth_headers, admin_headers):
    """GET /api/sessions/{id} auf fremde Session als normaler User → 403."""
    # Admin erstellt eine Session
    response = client.post("/api/sessions", headers=admin_headers, json={
        "agent_id": "test-agent-001",
        "title": "Admin Session"
    })
    assert response.status_code == 201
    session_id = response.json()["id"]
    
    # Normaler User versucht darauf zuzugreifen
    response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "session_no_access"


def test_admin_can_access_foreign_session(client, auth_headers, admin_headers):
    """Admin kann auf fremde Session zugreifen."""
    # User erstellt Session
    response = client.post("/api/sessions", headers=auth_headers, json={
        "agent_id": "test-agent-001",
        "title": "User Session"
    })
    assert response.status_code == 201
    session_id = response.json()["id"]
    
    # Admin greift darauf zu
    response = client.get(f"/api/sessions/{session_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["user_id"] == "testuser"


def test_user_can_access_own_session(client, auth_headers):
    """User kann auf eigene Session zugreifen."""
    # Session erstellen
    response = client.post("/api/sessions", headers=auth_headers, json={
        "agent_id": "test-agent-001",
        "title": "My Session"
    })
    assert response.status_code == 201
    session_id = response.json()["id"]
    
    # Auf eigene Session zugreifen
    response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["user_id"] == "testuser"


def test_create_session_invalid_agent(client, auth_headers):
    """POST /api/sessions mit ungültigem Agent → 404."""
    response = client.post("/api/sessions", headers=auth_headers, json={
        "agent_id": "nonexistent-agent",
        "title": "Should Fail"
    })
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "agent_not_found"
