from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import job_protocol, jobs
from hydrahive.containers import db as cdb
from hydrahive.containers import remote
from hydrahive.db.connection import db, init_db
from hydrahive.settings import settings


@pytest.fixture
def remote_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "remote.db", raising=False)
    init_db()
    node = node_db.create_node(
        node_id="node-remote",
        name="Remote Node",
        certificate_fingerprint="ab" * 32,
        capabilities={"incus": True, "instance_types": ["container"]},
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    return node.node_id


def _container(node_id: str, name: str = "remote-demo"):
    return cdb.create(
        owner="admin",
        name=name,
        image="images:debian/12",
        cpu=2,
        ram_mb=512,
        network_mode="isolated",
        node_id=node_id,
    )


def test_remote_create_queues_generation_bound_job(remote_db: str) -> None:
    container = _container(remote_db)
    queued = remote.queue_create(container.container_id, actor="admin-id")

    current = cdb.get(container.container_id)
    assert current.actual_state == "starting"
    assert current.desired_state == "running"
    assert current.generation == 1
    assert queued.node_id == remote_db
    assert queued.operation == "container.create"
    assert queued.generation == current.generation
    assert queued.payload == {
        "name": "remote-demo",
        "image": "images:debian/12",
        "cpu": 2,
        "ram_mb": 512,
        "network_mode": "isolated",
    }


def test_job_insert_failure_rolls_back_container_transition(remote_db: str, monkeypatch) -> None:
    container = _container(remote_db)
    before = cdb.get(container.container_id)

    def fail_create(**kwargs):
        raise jobs.JobConflict("node raced offline")

    monkeypatch.setattr(jobs, "create_job", fail_create)
    with pytest.raises(remote.RemoteContainerError, match="stopped accepting"):
        remote.queue_create(container.container_id, actor="admin-id")

    assert cdb.get(container.container_id) == before


def test_agent_success_message_projects_remote_container_state(remote_db: str) -> None:
    container = _container(remote_db)
    created = remote.queue_create(container.container_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    assert claimed is not None and claimed.lease_id is not None
    jobs.start_job(created.job_id, claimed.lease_id)

    response = job_protocol.handle_message(
        remote_db,
        "job_succeeded",
        {
            "job_id": created.job_id,
            "lease_id": claimed.lease_id,
            "result": {"actual_state": "running", "runtime_ref": container.name},
        },
    )

    assert response == {"type": "ack"}
    assert cdb.get(container.container_id).actual_state == "running"


def test_invalid_agent_success_is_recorded_as_failed_job(remote_db: str) -> None:
    container = _container(remote_db)
    created = remote.queue_create(container.container_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    assert claimed is not None and claimed.lease_id is not None
    jobs.start_job(created.job_id, claimed.lease_id)

    response = job_protocol.handle_message(
        remote_db,
        "job_succeeded",
        {
            "job_id": created.job_id,
            "lease_id": claimed.lease_id,
            "result": {"actual_state": "running", "runtime_ref": "wrong-runtime"},
        },
    )

    assert response == {"type": "ack"}
    assert jobs.get_job(created.job_id).status == "failed"
    assert jobs.get_job(created.job_id).error_code == "agent_result_invalid"
    assert cdb.get(container.container_id).actual_state == "error"


def test_result_projection_failure_rolls_back_terminal_job(remote_db: str, monkeypatch) -> None:
    container = _container(remote_db)
    created = remote.queue_create(container.container_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    assert claimed is not None and claimed.lease_id is not None
    jobs.start_job(created.job_id, claimed.lease_id)

    def fail_projection(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(remote, "apply_success", fail_projection)
    with pytest.raises(RuntimeError, match="boom"):
        job_protocol.handle_message(
            remote_db,
            "job_succeeded",
            {
                "job_id": created.job_id,
                "lease_id": claimed.lease_id,
                "result": {"actual_state": "running", "runtime_ref": container.name},
            },
        )

    assert jobs.get_job(created.job_id).status == "running"
    assert cdb.get(container.container_id).actual_state == "starting"


def test_remote_lifecycle_queues_jobs_and_offline_node_fails_before_state_change(remote_db: str) -> None:
    container = _container(remote_db)
    create = remote.queue_create(container.container_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    jobs.start_job(create.job_id, claimed.lease_id)
    result = {"actual_state": "running", "runtime_ref": container.name}
    jobs.succeed_job(create.job_id, claimed.lease_id, result)
    remote.apply_success(jobs.get_job(create.job_id), result)

    stop = remote.queue_lifecycle(container.container_id, "container.stop", actor="admin-id")
    assert stop.generation == 2
    assert cdb.get(container.container_id).actual_state == "stopping"

    node_db.transition_node_status(remote_db, "offline")
    before = cdb.get(container.container_id)
    with pytest.raises(remote.RemoteContainerError, match="cannot accept"):
        remote.queue_lifecycle(container.container_id, "container.start", actor="admin-id")
    assert cdb.get(container.container_id) == before


def test_draining_node_allows_stop_but_rejects_restart(remote_db: str) -> None:
    container = _container(remote_db)
    create = remote.queue_create(container.container_id, actor="admin-id")
    remote.apply_success(create, {"actual_state": "running", "runtime_ref": container.name})
    node_db.transition_node_status(remote_db, "draining")

    before = cdb.get(container.container_id)
    with pytest.raises(remote.RemoteContainerError, match="cannot accept"):
        remote.queue_lifecycle(container.container_id, "container.restart", actor="admin-id")
    assert cdb.get(container.container_id) == before

    stop = remote.queue_lifecycle(container.container_id, "container.stop", actor="admin-id")
    assert stop.operation == "container.stop"


def test_job_results_update_only_matching_generation_and_delete_on_success(remote_db: str) -> None:
    container = _container(remote_db)
    create = remote.queue_create(container.container_id, actor="admin-id")
    remote.apply_success(create, {"actual_state": "running", "runtime_ref": container.name})
    assert cdb.get(container.container_id).actual_state == "running"

    stale = jobs.create_job(
        node_id=remote_db,
        resource_kind="container",
        resource_id=container.container_id,
        operation="container.stop",
        generation=0,
        payload={"name": container.name},
        idempotency_key="stale-result",
        created_by="admin-id",
    )
    remote.apply_success(stale, {"actual_state": "stopped"})
    assert cdb.get(container.container_id).actual_state == "running"
    assert not remote.success_result_is_valid(stale, {"actual_state": "invalid"})

    delete = remote.queue_lifecycle(container.container_id, "container.delete", actor="admin-id")
    remote.apply_success(delete, {"actual_state": "deleted"})
    assert cdb.get(container.container_id) is None


def test_cancel_and_running_lease_expiry_project_terminal_error(remote_db: str) -> None:
    cancelled_container = _container(remote_db, "cancelled-demo")
    cancelled_job = remote.queue_create(cancelled_container.container_id, actor="admin-id")
    jobs.cancel_job(cancelled_job.job_id, actor="admin-id")
    cancelled = cdb.get(cancelled_container.container_id)
    assert cancelled.actual_state == "error"
    assert cancelled.last_error_code == "job_cancelled"

    expired_container = _container(remote_db, "expired-demo")
    expired_job = remote.queue_create(expired_container.container_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db, lease_seconds=10)
    assert claimed is not None and claimed.job_id == expired_job.job_id and claimed.lease_id is not None
    jobs.start_job(expired_job.job_id, claimed.lease_id)
    with db() as conn:
        conn.execute(
            "UPDATE compute_jobs SET lease_until = '2000-01-01T00:00:00Z' WHERE job_id = ?",
            (expired_job.job_id,),
        )
    jobs.expire_leases()
    expired = cdb.get(expired_container.container_id)
    assert expired.actual_state == "error"
    assert expired.last_error_code == "lease_expired"


def test_failure_projection_is_structured_and_generation_fenced(remote_db: str) -> None:
    container = _container(remote_db)
    create = remote.queue_create(container.container_id, actor="admin-id")
    remote.apply_failure(create, "incus_operation_failed")

    current = cdb.get(container.container_id)
    assert current.actual_state == "error"
    assert current.last_error_code == "incus_operation_failed"
    assert current.last_error_params is None
