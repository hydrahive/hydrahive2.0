"""Signed job validation and crash-safe idempotent dispatch."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from hydrahive_node._job_execution import MAX_JOB_BYTES
from hydrahive_node.game_job_protocol import (
    GameSchemaError,
    VerifiedCancel,
    VerifiedGameJob,
    validate_cancel,
    validate_game_offer,
)
RESOURCE_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ALLOWED_OPERATIONS = frozenset(
    {
        "container.create",
        "container.start",
        "container.stop",
        "container.restart",
        "container.delete",
        "container.inspect",
        "vm.create_from_image",
        "vm.start",
        "vm.stop",
        "vm.restart",
        "vm.delete",
        "vm.inspect",
    }
)
LEGACY_OFFER_FIELDS = {
    "job_id",
    "node_id",
    "resource_kind",
    "resource_id",
    "operation",
    "generation",
    "payload",
    "idempotency_key",
    "lease_id",
    "lease_until",
}


class JobValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VerifiedJob:
    job_id: str
    node_id: str
    resource_kind: str
    resource_id: str | None
    operation: str
    generation: int
    payload: dict[str, object]
    idempotency_key: str
    lease_id: str
    lease_until: str


def canonical_offer(offer: dict) -> bytes:
    try:
        encoded = json.dumps(
            offer,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise JobValidationError("job offer contains invalid JSON") from exc
    if len(encoded) > MAX_JOB_BYTES:
        raise JobValidationError("job offer is too large")
    return encoded


def _decode(value: str) -> bytes:
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise JobValidationError("job signature encoding is invalid") from exc


VerifiedOffer = VerifiedJob | VerifiedGameJob


def _verify_signature(body: dict, signature: str, public_key: str) -> None:
    try:
        key = Ed25519PublicKey.from_public_bytes(_decode(public_key))
        key.verify(_decode(signature), canonical_offer(body))
    except (ValueError, InvalidSignature) as exc:
        raise JobValidationError("job signature is invalid") from exc


def _validate_lease(lease_until: object) -> None:
    try:
        parsed = datetime.fromisoformat(str(lease_until).replace("Z", "+00:00"))
    except ValueError as exc:
        raise JobValidationError("job lease expiry is invalid") from exc
    if parsed.tzinfo is None or parsed.astimezone(UTC) <= datetime.now(UTC):
        raise JobValidationError("job lease has expired")


def _transport_fields_are_exact(message: dict, expected: set[str]) -> bool:
    fields = set(message)
    if "sequence" in fields:
        sequence = message["sequence"]
        if type(sequence) is not int or sequence < 1:
            return False
        fields.remove("sequence")
    return fields == expected


def verify_offer(message: dict, public_key: str, expected_node_id: str) -> VerifiedOffer:
    if not _transport_fields_are_exact(message, {"type", "job", "signature"}) or message.get("type") != "job_offer":
        raise JobValidationError("job offer envelope is invalid")
    offer = message.get("job")
    signature = message.get("signature")
    if not isinstance(offer, dict) or not isinstance(signature, str):
        raise JobValidationError("job offer schema is invalid")
    _verify_signature(offer, signature, public_key)
    if offer.get("resource_kind") == "game_workspace" or "provider" in offer:
        try:
            verified = validate_game_offer(offer, expected_node_id)
        except GameSchemaError as exc:
            raise JobValidationError(str(exc)) from exc
        _validate_lease(verified.lease_until)
        return verified
    if set(offer) != LEGACY_OFFER_FIELDS:
        raise JobValidationError("job offer schema is invalid")
    if offer["node_id"] != expected_node_id:
        raise JobValidationError("job belongs to a different node")
    if offer["operation"] not in ALLOWED_OPERATIONS:
        raise JobValidationError("job operation is not allowed")
    if offer["resource_kind"] not in {"container", "vm"} or not str(offer["operation"]).startswith(
        f"{offer['resource_kind']}."
    ):
        raise JobValidationError("job resource kind is invalid")
    if type(offer["generation"]) is not int or offer["generation"] < 0 or not isinstance(offer["payload"], dict):
        raise JobValidationError("job payload is invalid")
    for field in ("job_id", "node_id", "idempotency_key", "lease_id", "lease_until"):
        if not isinstance(offer[field], str) or not 0 < len(offer[field]) <= 255:
            raise JobValidationError(f"job {field} is invalid")
    resource_id = offer["resource_id"]
    if not isinstance(resource_id, str) or RESOURCE_ID_RE.fullmatch(resource_id) is None:
        raise JobValidationError("job resource_id is invalid")
    _validate_lease(offer["lease_until"])
    return VerifiedJob(**offer)  # type: ignore[arg-type]


def verify_cancel_message(
    message: dict,
    public_key: str,
    *,
    expected_node_id: str,
    expected_job_id: str,
    expected_lease_id: str,
) -> VerifiedCancel:
    expected_fields = {"type", "job_id", "node_id", "lease_id", "cancel_deadline", "signature"}
    if not _transport_fields_are_exact(message, expected_fields):
        raise JobValidationError("job cancel envelope is invalid")
    if message.get("type") != "job_cancel" or not isinstance(message.get("signature"), str):
        raise JobValidationError("job cancel envelope is invalid")
    body = {key: message[key] for key in ("job_id", "node_id", "lease_id", "cancel_deadline")}
    _verify_signature(body, message["signature"], public_key)
    try:
        return validate_cancel(body, expected_node_id, expected_job_id, expected_lease_id)
    except GameSchemaError as exc:
        raise JobValidationError(str(exc)) from exc


def verified_from_dict(value: dict[str, object]) -> VerifiedOffer:
    if value.get("resource_kind") == "game_workspace":
        return VerifiedGameJob(**value)  # type: ignore[arg-type]
    return VerifiedJob(**value)  # type: ignore[arg-type]


from hydrahive_node._job_execution import execute_offer  # noqa: E402,F401
