"""Public, rate-limited bootstrap endpoint for compute-node agents."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from hydrahive.api.middleware.errors import coded
from hydrahive.api.middleware.inbound_ratelimit import check_rate
from hydrahive.compute import enroll_service, enrollment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/compute/agent", tags=["compute-agent"])
ENROLL_IP_RATE_LIMIT = 60
ENROLL_TOKEN_RATE_LIMIT = 5
MAX_ENROLL_BODY_BYTES = 96 * 1024


class AgentEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=128)
    csr_pem: str = Field(min_length=1, max_length=20_000)
    protocol_version: int = Field(default=1, ge=1, le=1)
    agent_version: str = Field(min_length=1, max_length=64)
    capabilities: dict[str, object] = Field(default_factory=dict)
    resources: dict[str, object] = Field(default_factory=dict)


def _client_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    return f"compute-enroll:{host}"


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_agent(request: Request) -> dict:
    allowed, retry_after = check_rate(_client_key(request), limit=ENROLL_IP_RATE_LIMIT)
    if not allowed:
        raise coded(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", retry_after=retry_after)
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_ENROLL_BODY_BYTES:
            raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "compute_enrollment_body_too_large")
    try:
        body = AgentEnrollmentRequest.model_validate_json(bytes(content))
    except ValidationError:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_enrollment_invalid")
    token_key = f"compute-enroll-token:{hashlib.sha256(body.token.encode('utf-8')).hexdigest()}"
    token_allowed, token_retry_after = check_rate(token_key, limit=ENROLL_TOKEN_RATE_LIMIT)
    if not allowed or not token_allowed:
        raise coded(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            retry_after=max(retry_after, token_retry_after),
        )
    try:
        result = enroll_service.enroll_node(
            token=body.token,
            csr_pem=body.csr_pem,
            protocol_version=body.protocol_version,
            agent_version=body.agent_version,
            capabilities=body.capabilities,
            resources=body.resources,
        )
    except enrollment.EnrollmentError:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_enrollment_invalid")
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "compute_enrollment_invalid")
    except Exception:
        logger.exception("compute enrollment failed after input validation")
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "compute_enrollment_unavailable")
    return asdict(result)
