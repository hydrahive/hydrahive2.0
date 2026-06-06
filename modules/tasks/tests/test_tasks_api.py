"""API-Tests für das Tasks-Modul."""
from __future__ import annotations

BASE = "/api/modules/tasks/tasks"


def test_list_empty(client, alice):
    r = client.get(BASE, headers=alice)
    assert r.status_code == 200
    assert r.json() == []


def test_create_task(client, alice):
    r = client.post(BASE, json={"title": "Einkaufen gehen"}, headers=alice)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Einkaufen gehen"
    assert data["status"] == "open"
    assert data["priority"] == "medium"
    assert "id" in data


def test_create_task_with_all_fields(client, alice):
    r = client.post(BASE, json={
        "title": "Feature bauen",
        "description": "Tasks-Modul implementieren",
        "priority": "high",
        "project_id": "hydrahive2",
    }, headers=alice)
    assert r.status_code == 201
    data = r.json()
    assert data["priority"] == "high"
    assert data["project_id"] == "hydrahive2"
    assert data["description"] == "Tasks-Modul implementieren"


def test_list_returns_created_task(client, alice):
    client.post(BASE, json={"title": "Task A"}, headers=alice)
    client.post(BASE, json={"title": "Task B", "priority": "high"}, headers=alice)
    r = client.get(BASE, headers=alice)
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert "Task A" in titles
    assert "Task B" in titles


def test_high_priority_sorted_first(client, alice):
    client.post(BASE, json={"title": "Low",    "priority": "low"},    headers=alice)
    client.post(BASE, json={"title": "High",   "priority": "high"},   headers=alice)
    client.post(BASE, json={"title": "Medium", "priority": "medium"}, headers=alice)
    r = client.get(BASE, headers=alice)
    titles = [t["title"] for t in r.json()]
    assert titles.index("High") < titles.index("Medium") < titles.index("Low")


def test_filter_by_status(client, alice):
    r1 = client.post(BASE, json={"title": "Offen"}, headers=alice)
    task_id = r1.json()["id"]
    client.patch(f"{BASE}/{task_id}", json={"status": "done"}, headers=alice)
    client.post(BASE, json={"title": "Noch offen"}, headers=alice)

    r = client.get(BASE, params={"status": "open"}, headers=alice)
    assert all(t["status"] == "open" for t in r.json())
    assert len(r.json()) == 1


def test_update_status(client, alice):
    r = client.post(BASE, json={"title": "Erledigen"}, headers=alice)
    task_id = r.json()["id"]

    r = client.patch(f"{BASE}/{task_id}", json={"status": "done"}, headers=alice)
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_update_invalid_status(client, alice):
    r = client.post(BASE, json={"title": "Test"}, headers=alice)
    task_id = r.json()["id"]
    r = client.patch(f"{BASE}/{task_id}", json={"status": "flying"}, headers=alice)
    assert r.status_code == 422


def test_delete_task(client, alice):
    r = client.post(BASE, json={"title": "Löschen"}, headers=alice)
    task_id = r.json()["id"]

    r = client.delete(f"{BASE}/{task_id}", headers=alice)
    assert r.status_code == 204

    r = client.get(BASE, headers=alice)
    assert all(t["id"] != task_id for t in r.json())


def test_delete_not_found(client, alice):
    r = client.delete(f"{BASE}/nonexistent-id", headers=alice)
    assert r.status_code == 404


def test_user_isolation(client, alice, bob):
    """Alice sieht keine Tasks von Bob."""
    client.post(BASE, json={"title": "Alices Task"}, headers=alice)
    client.post(BASE, json={"title": "Bobs Task"}, headers=bob)

    alice_tasks = client.get(BASE, headers=alice).json()
    bob_tasks = client.get(BASE, headers=bob).json()

    assert all(t["title"] == "Alices Task" for t in alice_tasks)
    assert all(t["title"] == "Bobs Task" for t in bob_tasks)
    assert len(alice_tasks) == 1
    assert len(bob_tasks) == 1


def test_cannot_update_other_users_task(client, alice, bob):
    r = client.post(BASE, json={"title": "Alices Task"}, headers=alice)
    task_id = r.json()["id"]
    r = client.patch(f"{BASE}/{task_id}", json={"status": "done"}, headers=bob)
    assert r.status_code == 404


def test_unauthenticated_request(client):
    r = client.get(BASE)
    assert r.status_code == 401


def test_invalid_priority(client, alice):
    r = client.post(BASE, json={"title": "Test", "priority": "super-urgent"}, headers=alice)
    assert r.status_code == 422
