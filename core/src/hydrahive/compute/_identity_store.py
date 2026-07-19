"""Locked storage and validation for the local compute CA."""

from __future__ import annotations

import fcntl
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from hydrahive.settings import settings


@dataclass(frozen=True)
class CAState:
    key: ec.EllipticCurvePrivateKey
    certificate_pem: bytes
    certificate: x509.Certificate


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_file(path: Path, content: bytes, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
        published = os.open(path, os.O_RDONLY)
        try:
            os.fsync(published)
        finally:
            os.close(published)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def ca_lock() -> Iterator[None]:
    directory = settings.compute_pki_dir
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    lock_path = directory / ".ca.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.chmod(lock_path, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _validate_ca(key: object, certificate: x509.Certificate) -> ec.EllipticCurvePrivateKey:
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("compute CA key type is invalid")
    if certificate.subject != certificate.issuer:
        raise ValueError("compute CA is not self-issued")
    key_public = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    cert_public = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if key_public != cert_public:
        raise ValueError("compute CA key and certificate do not match")
    public_key = certificate.public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("compute CA certificate key type is invalid")
    try:
        public_key.verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,
            ec.ECDSA(certificate.signature_hash_algorithm),
        )
        constraints = certificate.extensions.get_extension_for_class(x509.BasicConstraints).value
        usage = certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    except (ValueError, x509.ExtensionNotFound) as exc:
        raise ValueError("compute CA certificate profile is invalid") from exc
    if not constraints.ca or constraints.path_length != 0 or not usage.key_cert_sign or not usage.crl_sign:
        raise ValueError("compute CA certificate profile is invalid")
    now = datetime.now(UTC)
    if certificate.not_valid_before_utc > now or certificate.not_valid_after_utc <= now:
        raise ValueError("compute CA certificate is not currently valid")
    return key


def load_ca() -> CAState | None:
    key_path = settings.compute_ca_key_path
    cert_path = settings.compute_ca_cert_path
    marker = settings.compute_pki_dir / ".initializing"
    if marker.exists() and (not key_path.is_file() or not cert_path.is_file()):
        key_path.unlink(missing_ok=True)
        cert_path.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
    if not key_path.exists() and not cert_path.exists():
        return None
    if not key_path.is_file() or not cert_path.is_file():
        raise ValueError("compute CA files are incomplete")
    try:
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        certificate_pem = cert_path.read_bytes()
        certificate = x509.load_pem_x509_certificate(certificate_pem)
        validated_key = _validate_ca(key, certificate)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("compute CA files are invalid") from exc
    os.chmod(key_path, 0o600)
    marker.unlink(missing_ok=True)
    return CAState(validated_key, certificate_pem, certificate)


def write_ca_pair(key_pem: bytes, certificate_pem: bytes) -> None:
    marker = settings.compute_pki_dir / ".initializing"
    _write_file(marker, b"initializing\n", 0o600)
    _write_file(settings.compute_ca_key_path, key_pem, 0o600)
    _write_file(settings.compute_ca_cert_path, certificate_pem, 0o644)
    marker.unlink()
    _fsync_directory(settings.compute_pki_dir)
