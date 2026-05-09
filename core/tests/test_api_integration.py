"""FastAPI Integration Tests für Auth- und Sessions-API.

Diese Tests verwenden FastAPI TestClient und eine temporäre SQLite-DB.
Fixtures (`client`, `auth_headers`, `admin_headers`, `setup_test_env`) leben
in conftest.py und werden auch von test_voice_chat genutzt.
"""
from __future__ import annotations


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
