"""Restricted on-disk identity storage for the node agent."""

from __future__ import annotations

import fcntl
import json
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentIdentity:
    server_url: str
    node_id: str
    certificate_fingerprint: str
    certificate_expires_at: str
    protocol_version: int = 1


@dataclass(frozen=True)
class StatePaths:
    directory: Path

    @property
    def identity(self) -> Path:
        return self.directory / "identity.json"

    @property
    def private_key(self) -> Path:
        return self.directory / "node-key.pem"

    @property
    def certificate(self) -> Path:
        return self.directory / "node-cert.pem"

    @property
    def ca_certificate(self) -> Path:
        return self.directory / "ca-cert.pem"

    @property
    def server_ca_certificate(self) -> Path:
        return self.directory / "server-ca.pem"

    @property
    def protocol_state(self) -> Path:
        return self.directory / "protocol-state.json"

    @property
    def job_signing_public_key(self) -> Path:
        return self.directory / "job-signing-public-key.txt"

    @property
    def job_results(self) -> Path:
        return self.directory / "job-results.json"

    @property
    def delivered_jobs(self) -> Path:
        return self.directory / "delivered-jobs.json"


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def save_identity(
    paths: StatePaths,
    identity: AgentIdentity,
    *,
    private_key_pem: bytes,
    certificate_pem: bytes,
    ca_certificate_pem: bytes,
    server_ca_certificate_pem: bytes | None = None,
) -> None:
    paths.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(paths.directory, 0o700)
    _atomic_write(paths.private_key, private_key_pem, 0o600)
    _atomic_write(paths.certificate, certificate_pem, 0o644)
    _atomic_write(paths.ca_certificate, ca_certificate_pem, 0o644)
    if server_ca_certificate_pem is not None:
        _atomic_write(paths.server_ca_certificate, server_ca_certificate_pem, 0o644)
    identity_json = json.dumps(asdict(identity), ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    _atomic_write(paths.identity, identity_json, 0o600)


def load_identity(paths: StatePaths) -> AgentIdentity:
    required = (paths.identity, paths.private_key, paths.certificate, paths.ca_certificate)
    if not all(path.is_file() for path in required):
        raise RuntimeError("node identity is incomplete; run hydrahive-node enroll")
    if paths.private_key.stat().st_mode & 0o077:
        raise RuntimeError("node private key permissions must be 0600")
    try:
        data = json.loads(paths.identity.read_text(encoding="utf-8"))
        identity = AgentIdentity(**data)
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("node identity is invalid") from exc
    if not identity.server_url.startswith("https://"):
        raise RuntimeError("node server URL must use HTTPS")
    return identity


def next_sequence(paths: StatePaths) -> int:
    lock_path = paths.directory / ".protocol-state.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            data = json.loads(paths.protocol_state.read_text(encoding="utf-8"))
            current = int(data["sequence"])
        except FileNotFoundError:
            current = 0
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RuntimeError("node protocol state is invalid") from exc
        sequence = current + 1
        _atomic_write(
            paths.protocol_state,
            json.dumps({"sequence": sequence}, separators=(",", ":")).encode("ascii"),
            0o600,
        )
        return sequence
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
