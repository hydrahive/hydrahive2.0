from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hydrahive_node import update_manifest


def _public(key: Ed25519PrivateKey) -> str:
    return (
        base64.urlsafe_b64encode(
            key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
        .decode("ascii")
        .rstrip("=")
    )


def _signed(key: Ed25519PrivateKey, manifest: dict) -> dict:
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = base64.urlsafe_b64encode(key.sign(body)).decode("ascii").rstrip("=")
    return {"type": "agent_update", "manifest": manifest, "signature": signature}


def _manifest(artifact: bytes, *, version: str = "2.1.0") -> dict:
    return {
        "version": version,
        "sha256": hashlib.sha256(artifact).hexdigest(),
        "size": len(artifact),
    }


def test_valid_manifest_and_matching_artifact_is_accepted() -> None:
    key = Ed25519PrivateKey.generate()
    artifact = b"new agent bytes"
    message = _signed(key, _manifest(artifact))

    verified = update_manifest.verify_update(message, _public(key), artifact, current_version="2.0.0")
    assert verified.version == "2.1.0"
    assert verified.sha256 == hashlib.sha256(artifact).hexdigest()


def test_tampered_signature_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    artifact = b"new agent bytes"
    message = _signed(key, _manifest(artifact))
    message["manifest"]["version"] = "9.9.9"  # break signature coverage

    with pytest.raises(update_manifest.UpdateManifestError):
        update_manifest.verify_update(message, _public(key), artifact, current_version="2.0.0")


def test_wrong_signing_key_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    artifact = b"new agent bytes"
    message = _signed(key, _manifest(artifact))

    with pytest.raises(update_manifest.UpdateManifestError):
        update_manifest.verify_update(message, _public(other), artifact, current_version="2.0.0")


def test_hash_mismatch_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    artifact = b"new agent bytes"
    message = _signed(key, _manifest(artifact))

    with pytest.raises(update_manifest.UpdateManifestError, match="hash"):
        update_manifest.verify_update(message, _public(key), b"different bytes", current_version="2.0.0")


def test_size_mismatch_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    artifact = b"new agent bytes"
    manifest = _manifest(artifact)
    manifest["size"] = 999  # inconsistent with real artifact
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = base64.urlsafe_b64encode(key.sign(body)).decode("ascii").rstrip("=")
    message = {"type": "agent_update", "manifest": manifest, "signature": signature}

    with pytest.raises(update_manifest.UpdateManifestError):
        update_manifest.verify_update(message, _public(key), artifact, current_version="2.0.0")


def test_downgrade_or_equal_version_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    artifact = b"older"
    message = _signed(key, _manifest(artifact, version="1.9.0"))

    with pytest.raises(update_manifest.UpdateManifestError, match="version"):
        update_manifest.verify_update(message, _public(key), artifact, current_version="2.0.0")


def test_malformed_envelope_is_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    with pytest.raises(update_manifest.UpdateManifestError):
        update_manifest.verify_update({"type": "wrong"}, _public(key), b"x", current_version="2.0.0")
