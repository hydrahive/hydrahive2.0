"""Gemeinsame PKCE- und Token-Helpers für alle OAuth-Provider."""
from __future__ import annotations

import base64
import hashlib
import secrets


REFRESH_THRESHOLD_S = 300


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_pkce() -> tuple[str, str]:
    """PKCE: liefert (verifier, challenge) — challenge ist S256(verifier)."""
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def make_state() -> str:
    return b64url(secrets.token_bytes(16))
