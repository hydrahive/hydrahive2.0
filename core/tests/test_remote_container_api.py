from __future__ import annotations

from hydrahive.api.routes import containers_crud
from hydrahive.compute import db as node_db
from hydrahive.compute import jobs
from hydrahive.containers import db as cdb
from hydrahive.containers import remote


def _online_remote_node() -> str:
    node_id = "node-remote-api"
    if node_db.get_node(node_id) is None:
        node_db.create_node(
            node_id=node_id,
            name="Remote API Node",
            certificate_fingerprint="ac" * 32,
            capabilities={"incus": True, "instance_types": ["container"]},
        )
        node_db.approve_node(node_id, "admin")
        node_db.transition_node_status(node_id, "online")
    return node_id


def test_remote_container_create_lifecycle_and_delete_queue_jobs(client, admin_headers, monkeypatch) -> None:
    node_id = _online_remote_node()
    monkeypatch.setattr(
        containers_crud.incus,
        "is_available",
        lambda: (_ for _ in ()).throw(AssertionError("remote create must not require local Incus")),
    )
    created = client.post(
        "/api/containers",
        headers=admin_headers,
        json={
            "name": "remote-api-demo",
            "image": "debian/12",
            "network_mode": "isolated",
            "node_id": node_id,
        },
    )
    assert created.status_code == 201
    container = created.json()
    assert container["node_id"] == node_id
    assert container["actual_state"] == "starting"

    create_job = jobs.list_jobs(node_id=node_id, status="queued")[0]
    assert create_job.operation == "container.create"
    remote.apply_success(create_job, {"actual_state": "running", "runtime_ref": container["name"]})

    info = client.get(f"/api/containers/{container['container_id']}/info", headers=admin_headers)
    assert info.status_code == 200
    assert info.json()["refresh_queued"] is False
    assert not any(job.operation == "container.inspect" for job in jobs.list_jobs(node_id=node_id))
    refresh = client.post(f"/api/containers/{container['container_id']}/refresh", headers=admin_headers)
    assert refresh.status_code == 202
    assert any(job.operation == "container.inspect" for job in jobs.list_jobs(node_id=node_id))

    stopped = client.post(f"/api/containers/{container['container_id']}/stop", headers=admin_headers)
    assert stopped.status_code == 200
    assert stopped.json()["actual_state"] == "stopping"
    stop_job = next(job for job in jobs.list_jobs(node_id=node_id) if job.operation == "container.stop")
    remote.apply_success(stop_job, {"actual_state": "stopped"})

    deleted = client.delete(f"/api/containers/{container['container_id']}", headers=admin_headers)
    assert deleted.status_code == 204
    assert cdb.get(container["container_id"]).actual_state == "stopping"
    delete_job = next(job for job in jobs.list_jobs(node_id=node_id) if job.operation == "container.delete")
    remote.apply_success(delete_job, {"actual_state": "deleted"})
    assert cdb.get(container["container_id"]) is None
