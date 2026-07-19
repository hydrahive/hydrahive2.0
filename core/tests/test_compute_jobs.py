from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute import jobs
from hydrahive.db.connection import db, init_db
from hydrahive.settings import settings


@pytest.fixture
def jobs_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "jobs.db", raising=False)
    init_db()
    node = node_db.create_node(
        node_id="node-jobs",
        name="Jobs Node",
        certificate_fingerprint="ab" * 32,
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    return node.node_id


def _create(node_id: str, *, key: str = "container:create:one"):
    return jobs.create_job(
        node_id=node_id,
        resource_kind="container",
        resource_id="container-one",
        operation="container.create",
        generation=1,
        payload={"name": "container-one", "image": "images:debian/12"},
        idempotency_key=key,
        created_by="admin",
    )


def test_create_job_is_idempotent_and_appends_initial_event(jobs_db: str) -> None:
    created = _create(jobs_db)
    repeated = _create(jobs_db)

    assert repeated == created
    assert created.status == "queued"
    assert created.attempts == 0
    assert [event.event_type for event in jobs.list_events(created.job_id)] == ["queued"]

    with pytest.raises(jobs.JobConflict, match="idempotency"):
        jobs.create_job(
            node_id=jobs_db,
            resource_kind="container",
            resource_id="other",
            operation="container.start",
            generation=1,
            payload={},
            idempotency_key="container:create:one",
            created_by="admin",
        )


def test_claim_is_atomic_node_bound_and_lease_checked(jobs_db: str) -> None:
    queued = _create(jobs_db)
    claimed = jobs.claim_next_job(jobs_db, lease_seconds=30)

    assert claimed is not None
    assert claimed.job_id == queued.job_id
    assert claimed.status == "leased"
    assert claimed.lease_id
    assert claimed.lease_until
    assert claimed.attempts == 1
    assert jobs.claim_next_job(jobs_db, lease_seconds=30) is None
    assert jobs.claim_next_job("other-node", lease_seconds=30) is None

    with pytest.raises(jobs.JobConflict, match="lease"):
        jobs.start_job(claimed.job_id, "wrong-lease")


def test_running_job_reports_progress_and_terminal_result_idempotently(jobs_db: str) -> None:
    created = _create(jobs_db)
    claimed = jobs.claim_next_job(jobs_db)
    assert claimed is not None and claimed.lease_id is not None

    running = jobs.start_job(created.job_id, claimed.lease_id)
    assert running.status == "running"
    assert running.started_at is not None
    progressed = jobs.report_progress(created.job_id, claimed.lease_id, 40, {"phase": "launch"})
    assert progressed.progress == 40

    succeeded = jobs.succeed_job(created.job_id, claimed.lease_id, {"runtime_ref": "container-one"})
    repeated = jobs.succeed_job(created.job_id, claimed.lease_id, {"runtime_ref": "container-one"})
    assert repeated == succeeded
    assert succeeded.status == "succeeded"
    assert succeeded.progress == 100
    assert succeeded.finished_at is not None
    assert [event.event_type for event in jobs.list_events(created.job_id)] == [
        "queued",
        "leased",
        "running",
        "progress",
        "succeeded",
    ]

    with pytest.raises(jobs.JobConflict, match="terminal"):
        jobs.fail_job(created.job_id, claimed.lease_id, "late_failure", {})


def test_expired_lease_requeues_unstarted_but_expires_running_job(jobs_db: str) -> None:
    first = _create(jobs_db, key="first")
    first_claim = jobs.claim_next_job(jobs_db, lease_seconds=30)
    assert first_claim is not None and first_claim.lease_id
    second = _create(jobs_db, key="second")
    second_claim = jobs.claim_next_job(jobs_db, lease_seconds=30)
    assert second_claim is not None and second_claim.lease_id
    jobs.start_job(second.job_id, second_claim.lease_id)

    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    with db() as conn:
        conn.execute(
            "UPDATE compute_jobs SET lease_until = ? WHERE job_id IN (?, ?)",
            (expired, first.job_id, second.job_id),
        )

    assert jobs.expire_leases() == (1, 1)
    assert jobs.get_job(first.job_id).status == "queued"
    assert jobs.get_job(second.job_id).status == "expired"


def test_cancel_rejects_terminal_job_and_every_transition_is_audited(jobs_db: str) -> None:
    created = _create(jobs_db)
    cancelled = jobs.cancel_job(created.job_id, actor="admin")
    assert cancelled.status == "cancelled"

    with pytest.raises(jobs.JobConflict, match="terminal"):
        jobs.cancel_job(created.job_id, actor="admin")

    with db() as conn:
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM compute_audit_log WHERE node_id = ? AND action LIKE 'job.%' ORDER BY created_at",
                (jobs_db,),
            )
        ]
    assert actions == ["job.queued", "job.cancelled"]
