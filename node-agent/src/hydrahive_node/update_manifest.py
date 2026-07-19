"""Signed agent-update manifest verification.

An agent update is only accepted when its manifest is Ed25519-signed by the
master (the same signing key that signs jobs) and the downloaded artifact's
SHA-256 and size match the signed manifest, and the version is strictly newer
than the running one. This prevents downgrade and tampered-binary attacks.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_MANIFEST_BYTES = 8 * 1024
MANIFEST_FIELDS = {"version", "sha256", "size"}
MAX_ARTIFACT_BYTES = 128 * 1024 * 1024


class UpdateManifestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VerifiedUpdate:
    version: str
    sha256: str
    size: int


def _decode(value: str) -> bytes:
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise UpdateManifestError("update signature encoding is invalid") from exc


def _canonical(manifest: dict) -> bytes:
    try:
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise UpdateManifestError("update manifest contains invalid JSON") from exc
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise UpdateManifestError("update manifest is too large")
    return encoded


def _parse_version(value: str) -> tuple[int, ...]:
    try:
        parts = tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError) as exc:
        raise UpdateManifestError("update version is invalid") from exc
    if not parts or any(part < 0 for part in parts):
        raise UpdateManifestError("update version is invalid")
    return parts


def verify_update(
    message: dict,
    public_key: str,
    artifact: bytes,
    *,
    current_version: str,
) -> VerifiedUpdate:
    if set(message) != {"type", "manifest", "signature"} or message.get("type") != "agent_update":
        raise UpdateManifestError("update envelope is invalid")
    manifest = message.get("manifest")
    signature = message.get("signature")
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS or not isinstance(signature, str):
        raise UpdateManifestError("update manifest schema is invalid")

    version = manifest["version"]
    sha256 = manifest["sha256"]
    size = manifest["size"]
    if not isinstance(version, str) or not 0 < len(version) <= 64:
        raise UpdateManifestError("update version is invalid")
    if not isinstance(sha256, str) or len(sha256) != 64 or not all(c in "0123456789abcdef" for c in sha256):
        raise UpdateManifestError("update hash is invalid")
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_ARTIFACT_BYTES:
        raise UpdateManifestError("update size is invalid")

    try:
        key = Ed25519PublicKey.from_public_bytes(_decode(public_key))
        key.verify(_decode(signature), _canonical(manifest))
    except (ValueError, InvalidSignature) as exc:
        raise UpdateManifestError("update signature is invalid") from exc

    if len(artifact) != size:
        raise UpdateManifestError("update artifact size does not match manifest")
    if hashlib.sha256(artifact).hexdigest() != sha256:
        raise UpdateManifestError("update artifact hash does not match manifest")

    if _parse_version(version) <= _parse_version(current_version):
        raise UpdateManifestError("update version is not newer than the running agent")

    return VerifiedUpdate(version=version, sha256=sha256, size=size)
