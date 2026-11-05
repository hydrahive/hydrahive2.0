from __future__ import annotations

import json

import pytest

from hydrahive.db import db, init_db, session_pages
from hydrahive.settings import settings


@pytest.fixture
def page_client(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "session-list-page.db", raising=False)
    init_db()
    return client


def _insert_session(
    session_id: str,
    *,
    user_id: str = "testuser",
    project_id: str | None = None,
    updated_at: str = "2026-01-01T00:00:00+00:00",
    metadata: dict | None = None,
) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO sessions
               (id, agent_id, project_id, user_id, title, created_at, updated_at, status, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                "test-agent-user",
                project_id,
                user_id,
                session_id,
                updated_at,
                updated_at,
                "active",
                json.dumps(metadata) if metadata is not None else None,
            ),
        )


def _mark_as_handoff(session_id: str) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO agent_handoffs
               (id, incoming_state_id, from_agent, agent_id, session_id, status, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"handoff-{session_id}",
                f"state-{session_id}",
                "source-agent",
                "test-agent-user",
                session_id,
                "running",
                "2026-01-01T00:00:00+00:00",
            ),
        )


def test_page_hides_handoff_sessions_but_keeps_promoted(page_client, auth_headers):
    _insert_session("normal", updated_at="2026-01-01T00:01:00+00:00")
    _insert_session("internal", updated_at="2026-01-01T00:02:00+00:00")
    _insert_session(
        "promoted",
        updated_at="2026-01-01T00:03:00+00:00",
        metadata={"user_visible": True},
    )
    _mark_as_handoff("internal")
    _mark_as_handoff("promoted")

    response = page_client.get("/api/sessions/page", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == ["promoted", "normal"]
    assert response.json()["total"] == 2

    internal_response = page_client.get(
        "/api/sessions/page?include_internal=true",
        headers=auth_headers,
    )
    assert internal_response.status_code == 200, internal_response.text
    assert [item["id"] for item in internal_response.json()["items"]] == [
        "promoted",
        "internal",
        "normal",
    ]
    assert internal_response.json()["total"] == 3


def test_malformed_metadata_does_not_break_visibility_filter(page_client, auth_headers):
    _insert_session("malformed")
    _mark_as_handoff("malformed")
    with db() as conn:
        conn.execute("UPDATE sessions SET metadata = ? WHERE id = ?", ("{not-json", "malformed"))

    response = page_client.get("/api/sessions/page", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_page_is_scoped_to_authenticated_user(page_client, auth_headers):
    _insert_session("own-session")
    _insert_session("foreign-session", user_id="admin")
    _mark_as_handoff("foreign-session")

    unauthenticated = page_client.get("/api/sessions/page")
    response = page_client.get("/api/sessions/page", headers=auth_headers)
    internal_response = page_client.get(
        "/api/sessions/page?include_internal=true",
        headers=auth_headers,
    )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == ["own-session"]
    assert response.json()["total"] == 1
    assert [item["id"] for item in internal_response.json()["items"]] == ["own-session"]
    assert internal_response.json()["total"] == 1


def test_newer_handoffs_do_not_displace_older_project_chat(page_client, auth_headers):
    _insert_session(
        "project-chat",
        project_id="project-a",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    for index in range(60):
        session_id = f"handoff-{index:02d}"
        _insert_session(
            session_id,
            project_id="project-a",
            updated_at=f"2026-01-02T00:{index:02d}:00+00:00",
        )
        _mark_as_handoff(session_id)

    response = page_client.get("/api/sessions/page?project_id=project-a", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == ["project-chat"]
    assert response.json()["total"] == 1


def test_page_paginates_more_than_50_sessions(page_client, auth_headers):
    for index in range(55):
        _insert_session(
            f"session-{index:02d}",
            updated_at=f"2026-01-01T00:{index:02d}:00+00:00",
        )

    first = page_client.get("/api/sessions/page", headers=auth_headers)
    second = page_client.get("/api/sessions/page?offset=50", headers=auth_headers)

    assert first.status_code == 200, first.text
    assert first.json()["limit"] == 50
    assert first.json()["offset"] == 0
    assert first.json()["total"] == 55
    assert first.json()["has_more"] is True
    assert len(first.json()["items"]) == 50
    assert [item["id"] for item in second.json()["items"]] == [
        "session-04",
        "session-03",
        "session-02",
        "session-01",
        "session-00",
    ]
    assert second.json()["total"] == 55
    assert second.json()["has_more"] is False


def test_page_scopes_project_and_unassigned(page_client, auth_headers):
    _insert_session("project-a", project_id="project-a")
    _insert_session("project-b", project_id="project-b")
    _insert_session("unassigned")

    project_response = page_client.get(
        "/api/sessions/page?project_id=project-a",
        headers=auth_headers,
    )
    unassigned_response = page_client.get(
        "/api/sessions/page?unassigned=true",
        headers=auth_headers,
    )

    assert project_response.status_code == 200, project_response.text
    assert [item["id"] for item in project_response.json()["items"]] == ["project-a"]
    assert project_response.json()["total"] == 1
    assert unassigned_response.status_code == 200, unassigned_response.text
    assert [item["id"] for item in unassigned_response.json()["items"]] == ["unassigned"]
    assert unassigned_response.json()["total"] == 1


def test_page_rejects_conflicting_scope_and_invalid_bounds(page_client, auth_headers):
    conflicting = page_client.get(
        "/api/sessions/page?project_id=project-a&unassigned=true",
        headers=auth_headers,
    )

    assert conflicting.status_code == 400
    assert conflicting.json()["detail"]["code"] == "session_scope_conflict"
    for query in (
        "limit=0", "limit=201", "offset=-1", "offset=10001",
        f"offset={2**63}", "project_id=", f"project_id={'x' * 65}",
    ):
        response = page_client.get(f"/api/sessions/page?{query}", headers=auth_headers)
        assert response.status_code == 422, (query, response.text)


def test_store_rejects_invalid_bounds_and_conflicting_scope(page_client):
    with pytest.raises(ValueError, match="bounds"):
        session_pages.list_page_for_user("testuser", limit=0)
    with pytest.raises(ValueError, match="bounds"):
        session_pages.list_page_for_user("testuser", offset=-1)
    with pytest.raises(ValueError, match="bounds"):
        session_pages.list_page_for_user("testuser", offset=10_001)
    with pytest.raises(ValueError, match="scope"):
        session_pages.list_page_for_user("testuser", project_id="p", unassigned=True)


def test_migration_adds_agent_handoff_session_index(page_client):
    with db() as conn:
        indexes = conn.execute("PRAGMA index_list('agent_handoffs')").fetchall()

    assert "idx_agent_handoffs_session_id" in {row["name"] for row in indexes}


def test_legacy_list_remains_unfiltered(page_client, auth_headers):
    _insert_session("legacy-handoff")
    _mark_as_handoff("legacy-handoff")

    response = page_client.get("/api/sessions", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert [item["id"] for item in response.json()] == ["legacy-handoff"]
