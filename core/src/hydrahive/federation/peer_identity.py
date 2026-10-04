"""Eigene Server-Identität für die Server-Kopplung (docs/specs/server-peering.md).

Jeder HydraHive-Server hat ein Ed25519-Schlüsselpaar. Der private Schlüssel
liegt nur in ``$HH_DATA_DIR/peering/server_ed25519`` (0600) und verlässt den
Server nie. Weitergegeben wird nur der öffentliche Schlüssel im Kopplungscode.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from hydrahive.settings import settings

logger = logging.getLogger(__name__)

_CODE_PREFIX = "hhpeer1:"


def _key_path() -> Path:
    return Path(str(settings.data_dir)) / "peering" / "server_ed25519"


def _load_or_create() -> Ed25519PrivateKey:
    path = _key_path()
    if path.is_file():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)  # type: ignore[return-value]
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    # O_EXCL: zwei gleichzeitige Starts dürfen sich nicht gegenseitig überschreiben.
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return serialization.load_pem_private_key(path.read_bytes(), password=None)  # type: ignore[return-value]
    with os.fdopen(fd, "wb") as f:
        f.write(pem)
    logger.info("Server-Kopplung: neues Schlüsselpaar angelegt (%s)", fingerprint(public_key_b64(key)))
    return key


def _raw_public(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def public_key_b64(key: Ed25519PrivateKey | None = None) -> str:
    return base64.b64encode(_raw_public(key or _load_or_create())).decode()


def fingerprint(public_key: str) -> str:
    """Kurzer, vergleichbarer Fingerprint: SHA256, 8 Vierergruppen."""
    digest = hashlib.sha256(base64.b64decode(public_key)).hexdigest()[:32]
    return " ".join(digest[i:i + 4] for i in range(0, 32, 4))


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def sign(payload: dict) -> str:
    return base64.b64encode(_load_or_create().sign(canonical(payload))).decode()


def verify(public_key: str, payload: dict, signature: str) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True))
        pub.verify(base64.b64decode(signature, validate=True), canonical(payload))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def valid_public_key(public_key: str) -> bool:
    try:
        raw = base64.b64decode(public_key, validate=True)
        Ed25519PublicKey.from_public_bytes(raw)
        return len(raw) == 32
    except (ValueError, TypeError):
        return False


def pairing_code(name: str, url: str) -> str:
    """Kopplungscode: Name, URL und öffentlicher Schlüssel, ohne Geheimnis."""
    body = {"name": name, "url": url.rstrip("/"), "public_key": public_key_b64()}
    return _CODE_PREFIX + base64.urlsafe_b64encode(canonical(body)).decode()


def parse_pairing_code(code: str) -> dict:
    """Liest einen Kopplungscode. ValueError bei kaputtem oder fremdem Format."""
    code = (code or "").strip()
    if not code.startswith(_CODE_PREFIX):
        raise ValueError("kein HydraHive-Kopplungscode")
    try:
        body = json.loads(base64.urlsafe_b64decode(code[len(_CODE_PREFIX):]))
    except (ValueError, TypeError) as exc:
        raise ValueError("Kopplungscode ist beschädigt") from exc
    if not isinstance(body, dict):
        raise ValueError("Kopplungscode ist beschädigt")
    name, url, pub = body.get("name"), body.get("url"), body.get("public_key")
    if not all(isinstance(v, str) and v for v in (name, url, pub)):
        raise ValueError("Kopplungscode unvollständig")
    if not valid_public_key(pub):
        raise ValueError("Kopplungscode enthält keinen gültigen Schlüssel")
    return {"name": name, "url": url.rstrip("/"), "public_key": pub}
