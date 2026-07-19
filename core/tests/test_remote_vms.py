from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import job_protocol, jobs
from hydrahive.vms import db as vmdb
from hydrahive.vms import remote
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
        capabilities={"incus": True, "kvm": True, "instance_types": ["container", "vm"]},
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    return node.node_id


def _vm(node_id: str, name: str = "remotevm"):
    return vmdb.create_vm(
        owner="admin",
        name=name,
        cpu=2,
        ram_mb=2048,
        disk_gb=20,
        qcow2_path="",
        network_mode="bridged",
        node_id=node_id,
        runtime="incus",
        runtime_ref=None,
        image="images:debian/12",
    )


def test_remote_vm_create_queues_generation_bound_job(remote_db: str) -> None:
    vm = _vm(remote_db)
    queued = remote.queue_create(vm.vm_id, actor="admin-id")

    current = vmdb.get_vm(vm.vm_id)
    assert current.actual_state == "starting"
    assert current.desired_state == "running"
    assert current.generation == 1
    assert queued.node_id == remote_db
    assert queued.operation == "vm.create_from_image"
    assert queued.resource_kind == "vm"
    assert queued.generation == current.generation
    assert queued.payload == {
        "name": "remotevm",
        "image": "images:debian/12",
        "cpu": 2,
        "ram_mb": 2048,
        "disk_gb": 20,
        "network_mode": "bridged",
    }


def test_job_insert_failure_rolls_back_vm_transition(remote_db: str, monkeypatch) -> None:
    vm = _vm(remote_db)
    before = vmdb.get_vm(vm.vm_id)

    def fail_create(**kwargs):
        raise jobs.JobConflict("node raced offline")

    monkeypatch.setattr(jobs, "create_job", fail_create)
    with pytest.raises(remote.RemoteVMError, match="stopped accepting"):
        remote.queue_create(vm.vm_id, actor="admin-id")

    assert vmdb.get_vm(vm.vm_id) == before


def test_agent_success_message_projects_remote_vm_state(remote_db: str) -> None:
    vm = _vm(remote_db)
    created = remote.queue_create(vm.vm_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    assert claimed is not None and claimed.lease_id is not None
    jobs.start_job(created.job_id, claimed.lease_id)

    response = job_protocol.handle_message(
        remote_db,
        "job_succeeded",
        {
            "job_id": created.job_id,
            "lease_id": claimed.lease_id,
            "result": {"actual_state": "running", "runtime_ref": vm.name},
        },
    )

    assert response == {"type": "ack"}
    current = vmdb.get_vm(vm.vm_id)
    assert current.actual_state == "running"
    assert current.runtime_ref == vm.name


def test_invalid_agent_success_is_recorded_as_failed_job(remote_db: str) -> None:
    vm = _vm(remote_db)
    created = remote.queue_create(vm.vm_id, actor="admin-id")
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
    assert vmdb.get_vm(vm.vm_id).actual_state == "error"


def test_remote_lifecycle_queues_jobs_and_offline_node_fails_before_state_change(remote_db: str) -> None:
    vm = _vm(remote_db)
    create = remote.queue_create(vm.vm_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db)
    jobs.start_job(create.job_id, claimed.lease_id)
    result = {"actual_state": "running", "runtime_ref": vm.name}
    jobs.succeed_job(create.job_id, claimed.lease_id, result)
    remote.apply_success(jobs.get_job(create.job_id), result)

    stop = remote.queue_lifecycle(vm.vm_id, "vm.stop", actor="admin-id")
    assert stop.generation == 2
    assert vmdb.get_vm(vm.vm_id).actual_state == "stopping"

    node_db.transition_node_status(remote_db, "offline")
    before = vmdb.get_vm(vm.vm_id)
    with pytest.raises(remote.RemoteVMError, match="cannot accept"):
        remote.queue_lifecycle(vm.vm_id, "vm.start", actor="admin-id")
    assert vmdb.get_vm(vm.vm_id) == before


def test_draining_node_allows_stop_but_rejects_restart(remote_db: str) -> None:
    vm = _vm(remote_db)
    create = remote.queue_create(vm.vm_id, actor="admin-id")
    remote.apply_success(create, {"actual_state": "running", "runtime_ref": vm.name})
    node_db.transition_node_status(remote_db, "draining")

    before = vmdb.get_vm(vm.vm_id)
    with pytest.raises(remote.RemoteVMError, match="cannot accept"):
        remote.queue_lifecycle(vm.vm_id, "vm.restart", actor="admin-id")
    assert vmdb.get_vm(vm.vm_id) == before

    stop = remote.queue_lifecycle(vm.vm_id, "vm.stop", actor="admin-id")
    assert stop.operation == "vm.stop"


def test_job_results_update_only_matching_generation_and_delete_on_success(remote_db: str) -> None:
    vm = _vm(remote_db)
    create = remote.queue_create(vm.vm_id, actor="admin-id")
    remote.apply_success(create, {"actual_state": "running", "runtime_ref": vm.name})
    assert vmdb.get_vm(vm.vm_id).actual_state == "running"

    stale = jobs.create_job(
        node_id=remote_db,
        resource_kind="vm",
        resource_id=vm.vm_id,
        operation="vm.stop",
        generation=0,
        payload={"name": vm.name},
        idempotency_key="stale-result",
        created_by="admin-id",
    )
    remote.apply_success(stale, {"actual_state": "stopped"})
    assert vmdb.get_vm(vm.vm_id).actual_state == "running"
    assert not remote.success_result_is_valid(stale, {"actual_state": "invalid"})

    delete = remote.queue_lifecycle(vm.vm_id, "vm.delete", actor="admin-id")
    remote.apply_success(delete, {"actual_state": "deleted"})
    assert vmdb.get_vm(vm.vm_id) is None


def test_cancel_and_running_lease_expiry_project_terminal_error(remote_db: str) -> None:
    cancelled_vm = _vm(remote_db, "cancelledvm")
    cancelled_job = remote.queue_create(cancelled_vm.vm_id, actor="admin-id")
    jobs.cancel_job(cancelled_job.job_id, actor="admin-id")
    cancelled = vmdb.get_vm(cancelled_vm.vm_id)
    assert cancelled.actual_state == "error"
    assert cancelled.last_error_code == "job_cancelled"

    expired_vm = _vm(remote_db, "expiredvm")
    expired_job = remote.queue_create(expired_vm.vm_id, actor="admin-id")
    claimed = jobs.claim_next_job(remote_db, lease_seconds=10)
    assert claimed is not None and claimed.job_id == expired_job.job_id and claimed.lease_id is not None
    jobs.start_job(expired_job.job_id, claimed.lease_id)
    with db() as conn:
        conn.execute(
            "UPDATE compute_jobs SET lease_until = '2000-01-01T00:00:00Z' WHERE job_id = ?",
            (expired_job.job_id,),
        )
    jobs.expire_leases()
    expired = vmdb.get_vm(expired_vm.vm_id)
    assert expired.actual_state == "error"
    assert expired.last_error_code == "lease_expired"


def test_failure_projection_is_structured_and_generation_fenced(remote_db: str) -> None:
    vm = _vm(remote_db)
    create = remote.queue_create(vm.vm_id, actor="admin-id")
    remote.apply_failure(create, "incus_operation_failed")

    current = vmdb.get_vm(vm.vm_id)
    assert current.actual_state == "error"
    assert current.last_error_code == "incus_operation_failed"
    assert current.last_error_params is None
