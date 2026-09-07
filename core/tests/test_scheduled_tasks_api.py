from __future__ import annotations

def test_create_list_and_pause_scheduled_task(client, auth_headers):
    created = client.post(
        "/api/scheduled-tasks",
        headers=auth_headers,
        json={
            "title": "Projekt prüfen",
            "prompt": "Prüfe den Workspace auf neue Fehler.",
            "target_type": "buddy",
            "target_id": "buddy",
            "interval_seconds": 10,
        },
    )
    assert created.status_code == 201
    task = created.json()
    assert task["execution_mode"] == "direct"
    assert task["interval_seconds"] == 10
    listed = client.get("/api/scheduled-tasks", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["task_id"] == task["task_id"] for item in listed.json())
    paused = client.post(f"/api/scheduled-tasks/{task['task_id']}/pause", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False


def test_interval_below_ten_seconds_is_rejected(client, auth_headers):
    response = client.post(
        "/api/scheduled-tasks",
        headers=auth_headers,
        json={"title": "zu schnell", "prompt": "x", "interval_seconds": 9},
    )
    assert response.status_code == 422


def test_non_admin_cannot_read_admin_schedule_list(client, auth_headers):
    response = client.get("/api/scheduled-tasks/admin/all", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "admin_only"
