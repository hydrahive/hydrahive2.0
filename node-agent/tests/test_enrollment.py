from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from hydrahive_node.enrollment import AgentEnrollmentError, enroll
from hydrahive_node.storage import StatePaths, load_identity


def _ca():
    key = ec.generate_private_key(ec.SECP384R1())
    now = datetime.now(UTC)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Compute CA")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .sign(key, hashes.SHA384())
    )
    return key, certificate


def _transport(*, fingerprint_override: str | None = None) -> httpx.MockTransport:
    ca_key, ca_certificate = _ca()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        csr = x509.load_pem_x509_csr(payload["csr_pem"].encode("ascii"))
        node_id = "019-node-test"
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, node_id)]))
            .issuer_name(ca_certificate.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), True)
            .add_extension(
                x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"urn:hydrahive:node:{node_id}")]),
                False,
            )
            .sign(ca_key, hashes.SHA384())
        )
        from cryptography.hazmat.primitives import serialization

        cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")
        ca_pem = ca_certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")
        fingerprint = fingerprint_override or certificate.fingerprint(hashes.SHA256()).hex()
        return httpx.Response(
            201,
            json={
                "node": {"node_id": node_id},
                "certificate_pem": cert_pem,
                "ca_certificate_pem": ca_pem,
                "certificate_fingerprint": fingerprint,
                "certificate_expires_at": certificate.not_valid_after_utc.isoformat(),
            },
        )

    return httpx.MockTransport(handler)


def test_enroll_validates_response_and_stores_restricted_identity(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")

    identity = enroll(
        server_url="https://hydrahive.test",
        token="x" * 43,
        node_name="Node Test",
        paths=paths,
        transport=_transport(),
    )

    assert identity.node_id == "019-node-test"
    assert load_identity(paths) == identity
    assert os.stat(paths.directory).st_mode & 0o777 == 0o700
    assert os.stat(paths.private_key).st_mode & 0o777 == 0o600
    assert os.stat(paths.identity).st_mode & 0o777 == 0o600
    assert "x" * 43 not in paths.identity.read_text()


def test_enroll_rejects_plain_http(tmp_path) -> None:
    with pytest.raises(AgentEnrollmentError, match="HTTPS"):
        enroll(
            server_url="http://hydrahive.test",
            token="x" * 43,
            node_name="Node Test",
            paths=StatePaths(tmp_path),
            transport=_transport(),
        )


def test_enroll_rejects_tampered_fingerprint_without_writing_key(tmp_path) -> None:
    paths = StatePaths(tmp_path / "state")
    with pytest.raises(AgentEnrollmentError, match="fingerprint"):
        enroll(
            server_url="https://hydrahive.test",
            token="x" * 43,
            node_name="Node Test",
            paths=paths,
            transport=_transport(fingerprint_override="00" * 32),
        )
    assert not paths.private_key.exists()
