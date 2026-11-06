"""Typed mapping between authenticated agent messages and durable jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hydrahive.compute import job_signing, jobs
from hydrahive.compute._job_cancel import pending_game_cancel
from hydrahive.compute.models import ComputeJob, JSONObject
from hydrahive.compute.providers.game_runtime_v1 import validate_game_offer
from hydrahive.db.connection import db

JOB_MESSAGE_TYPES = frozenset(
    {
        "job_poll", "job_control_poll", "job_started", "job_renew", "job_progress",
        "job_succeeded", "job_failed", "job_cancelled",
    }
)


class JobProtocolError(ValueError):
    pass


def _job_for_node(node_id: str, payload: dict[str, object]) -> tuple[ComputeJob, str]:
    job_id = payload.get("job_id")
    lease_id = payload.get("lease_id")
    if not isinstance(job_id, str) or not isinstance(lease_id, str):
        raise JobProtocolError("job payload is invalid")
    job = jobs.get_job(job_id)
    if job is None or job.node_id != node_id:
        raise JobProtocolError("job does not belong to authenticated node")
    return job, lease_id


def _object(payload: dict[str, object], key: str) -> JSONObject:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise JobProtocolError(f"job {key} is invalid")
    return value  # type: ignore[return-value]


def _offer(job: ComputeJob) -> dict:
    body = {
        "job_id": job.job_id,
        "node_id": job.node_id,
        "resource_kind": job.resource_kind,
        "resource_id": job.resource_id,
        "operation": job.operation,
        "generation": job.generation,
        "payload": job.payload,
        "idempotency_key": job.idempotency_key,
        "lease_id": job.lease_id,
        "lease_until": job.lease_until,
    }
    if job.resource_kind == "game_workspace":
        body.update(
            attempt_id=job.lease_id,
            provider=job.provider,
            project_id=job.project_id,
            game_resource_id=job.game_resource_id,
            workspace_generation=job.workspace_generation,
            source_commit_sha=job.source_commit_sha,
            source_snapshot_digest=job.source_snapshot_digest,
        )
        validate_game_offer(body)
    return {"type": "job_offer", "job": body, "signature": job_signing.sign_offer(body)}


def handle_message(node_id: str, message_type: str, payload: dict[str, object]) -> dict:
    if message_type not in JOB_MESSAGE_TYPES:
        raise JobProtocolError("unknown job message type")
    if message_type in {"job_poll", "job_control_poll"}:
        if payload:
            raise JobProtocolError("job poll payload must be empty")
        if message_type == "job_poll":
            claimed = jobs.claim_next_job(node_id, lease_seconds=300)
            return _offer(claimed) if claimed is not None else {"type": "no_job"}
        cancelled = pending_game_cancel(node_id)
        if cancelled is None:
            return {"type": "no_control"}
        body = {
            "job_id": cancelled.job_id,
            "node_id": cancelled.node_id,
            "lease_id": cancelled.lease_id,
            "cancel_deadline": (datetime.now(UTC) + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
        }
        return {"type": "job_cancel", **body, "signature": job_signing.sign_offer(body)}

    job, lease_id = _job_for_node(node_id, payload)
    try:
        if message_type == "job_started":
            if set(payload) != {"job_id", "lease_id"}:
                raise JobProtocolError("job started payload is invalid")
            started = jobs.start_job(job.job_id, lease_id)
            if started.status == "failed" and started.error_code == "job_rejected":
                return {"type": "job_rejected", "reason": "execution_binding_invalid"}
        elif message_type == "job_renew":
            if set(payload) != {"job_id", "lease_id"}:
                raise JobProtocolError("job renewal payload is invalid")
            jobs.renew_job_lease(job.job_id, lease_id)
        elif message_type == "job_cancelled":
            if set(payload) != {"job_id", "lease_id"}:
                raise JobProtocolError("job cancellation payload is invalid")
            jobs.confirm_game_job_cancelled(job.job_id, lease_id, node_id=node_id)
        elif message_type == "job_progress":
            if set(payload) != {"job_id", "lease_id", "progress", "data"}:
                raise JobProtocolError("job progress payload is invalid")
            progress = payload["progress"]
            if not isinstance(progress, int):
                raise JobProtocolError("job progress is invalid")
            jobs.report_progress(job.job_id, lease_id, progress, _object(payload, "data"))
        elif message_type == "job_succeeded":
            if set(payload) != {"job_id", "lease_id", "result"}:
                raise JobProtocolError("job result payload is invalid")
            result = _object(payload, "result")
            with db(immediate=True) as conn:
                if job.resource_kind == "container":
                    from hydrahive.containers import remote

                    if not remote.success_result_is_valid(job, result):
                        failed = jobs.fail_job(
                            job.job_id,
                            lease_id,
                            "agent_result_invalid",
                            {},
                            connection=conn,
                        )
                        remote.apply_failure(failed, "agent_result_invalid", connection=conn)
                    else:
                        completed = jobs.succeed_job(job.job_id, lease_id, result, connection=conn)
                        remote.apply_success(completed, result, connection=conn)
                elif job.resource_kind == "vm":
                    from hydrahive.vms import remote as vm_remote

                    if not vm_remote.success_result_is_valid(job, result):
                        failed = jobs.fail_job(
                            job.job_id,
                            lease_id,
                            "agent_result_invalid",
                            {},
                            connection=conn,
                        )
                        vm_remote.apply_failure(failed, "agent_result_invalid", connection=conn)
                    else:
                        completed = jobs.succeed_job(job.job_id, lease_id, result, connection=conn)
                        vm_remote.apply_success(completed, result, connection=conn)
                else:
                    jobs.succeed_job(job.job_id, lease_id, result, connection=conn)
        else:
            if set(payload) != {"job_id", "lease_id", "error_code", "error_params"}:
                raise JobProtocolError("job failure payload is invalid")
            error_code = payload["error_code"]
            if not isinstance(error_code, str):
                raise JobProtocolError("job error code is invalid")
            with db(immediate=True) as conn:
                failed = jobs.fail_job(
                    job.job_id,
                    lease_id,
                    error_code,
                    _object(payload, "error_params"),
                    connection=conn,
                )
                if failed.resource_kind == "container":
                    from hydrahive.containers import remote

                    remote.apply_failure(failed, error_code, connection=conn)
                elif failed.resource_kind == "vm":
                    from hydrahive.vms import remote as vm_remote

                    vm_remote.apply_failure(failed, error_code, connection=conn)
    except JobProtocolError:
        raise
    except jobs.JobConflict:
        return {"type": "job_rejected", "reason": "state_conflict"}
    except (jobs.JobNotFound, ValueError) as exc:
        raise JobProtocolError("job state update is invalid") from exc
    return {"type": "ack"}
