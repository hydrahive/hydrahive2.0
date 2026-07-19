"""Typed mapping between authenticated agent messages and durable jobs."""

from __future__ import annotations

from hydrahive.compute import job_signing, jobs
from hydrahive.compute.models import ComputeJob, JSONObject
from hydrahive.db.connection import db

JOB_MESSAGE_TYPES = frozenset({"job_poll", "job_started", "job_renew", "job_progress", "job_succeeded", "job_failed"})


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
    return {"type": "job_offer", "job": body, "signature": job_signing.sign_offer(body)}


def handle_message(node_id: str, message_type: str, payload: dict[str, object]) -> dict:
    if message_type not in JOB_MESSAGE_TYPES:
        raise JobProtocolError("unknown job message type")
    if message_type == "job_poll":
        if payload:
            raise JobProtocolError("job poll payload must be empty")
        claimed = jobs.claim_next_job(node_id, lease_seconds=300)
        return _offer(claimed) if claimed is not None else {"type": "no_job"}

    job, lease_id = _job_for_node(node_id, payload)
    try:
        if message_type == "job_started":
            if set(payload) != {"job_id", "lease_id"}:
                raise JobProtocolError("job started payload is invalid")
            jobs.start_job(job.job_id, lease_id)
        elif message_type == "job_renew":
            if set(payload) != {"job_id", "lease_id"}:
                raise JobProtocolError("job renewal payload is invalid")
            jobs.renew_job_lease(job.job_id, lease_id)
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
    except JobProtocolError:
        raise
    except jobs.JobConflict:
        return {"type": "job_rejected", "reason": "state_conflict"}
    except (jobs.JobNotFound, ValueError) as exc:
        raise JobProtocolError("job state update is invalid") from exc
    return {"type": "ack"}
