"""Strict versioned inbound message schema for the compute-agent channel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_CLOCK_SKEW_SECONDS = 120


class ProtocolError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class AgentMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "hello",
        "heartbeat",
        "capabilities",
        "job_poll",
        "job_started",
        "job_progress",
        "job_succeeded",
        "job_failed",
    ]
    protocol_version: Literal[1]
    node_id: str = Field(min_length=1, max_length=128)
    sequence: int = Field(ge=1, le=9_223_372_036_854_775_807)
    nonce: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    sent_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)


def parse_message(raw: str) -> AgentMessage:
    try:
        message = AgentMessage.model_validate_json(raw)
    except ValidationError as exc:
        raise ProtocolError("agent_message_invalid") from exc
    if message.sent_at.tzinfo is None:
        raise ProtocolError("agent_timestamp_invalid")
    if abs((datetime.now(UTC) - message.sent_at.astimezone(UTC)).total_seconds()) > MAX_CLOCK_SKEW_SECONDS:
        raise ProtocolError("agent_timestamp_invalid")
    return message
