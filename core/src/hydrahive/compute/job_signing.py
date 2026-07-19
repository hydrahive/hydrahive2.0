"""Dedicated Ed25519 signing key and canonical signatures for compute jobs."""

from __future__ import annotations

import base64
import fcntl
import json
import os
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from hydrahive.settings import settings


def canonical_offer(offer: dict) -> bytes:
    return json.dumps(offer, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")


def _private_key() -> Ed25519PrivateKey:
    directory = settings.compute_pki_dir
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = directory / "job-signing-key.bin"
    lock_path = directory / ".job-signing.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if key_path.exists():
            raw = key_path.read_bytes()
            if len(raw) != 32:
                raise RuntimeError("compute job signing key is invalid")
            os.chmod(key_path, 0o600)
            return Ed25519PrivateKey.from_private_bytes(raw)
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
        )
        temporary = key_path.with_name(f".{key_path.name}.{secrets.token_hex(8)}.tmp")
        temporary_descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(temporary_descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, key_path)
        finally:
            temporary.unlink(missing_ok=True)
        return key
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


def public_key_text() -> str:
    raw = _private_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return _encode(raw)


def sign_offer(offer: dict) -> str:
    return _encode(_private_key().sign(canonical_offer(offer)))


def verify_offer(offer: dict, signature: str, public_key: str) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(_decode(public_key))
        key.verify(_decode(signature), canonical_offer(offer))
    except (ValueError, TypeError, InvalidSignature):
        return False
    return True
