from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from hydrahive.compute import identity
from hydrahive.settings import settings


@pytest.fixture
def pki_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "compute-pki"
    monkeypatch.setattr(settings, "compute_pki_dir", directory, raising=False)
    monkeypatch.setattr(settings, "compute_ca_key_path", directory / "ca-key.pem", raising=False)
    monkeypatch.setattr(settings, "compute_ca_cert_path", directory / "ca-cert.pem", raising=False)
    return directory


def _csr(common_name: str = "Node A") -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    return (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
    )


def test_compute_ca_is_stable_and_private_key_is_mode_0600(pki_dir: Path) -> None:
    first = identity.ensure_compute_ca()
    second = identity.ensure_compute_ca()

    assert first.fingerprint == second.fingerprint
    assert first.certificate_pem == second.certificate_pem
    assert os.stat(settings.compute_ca_key_path).st_mode & 0o777 == 0o600
    assert settings.compute_ca_key_path.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")


def test_compute_ca_initialization_is_serialized(pki_dir: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        fingerprints = list(executor.map(lambda _: identity.ensure_compute_ca().fingerprint, range(16)))

    assert len(set(fingerprints)) == 1


def test_compute_ca_rejects_mismatched_key_and_certificate(pki_dir: Path) -> None:
    identity.ensure_compute_ca()
    unrelated_key = ec.generate_private_key(ec.SECP384R1())
    settings.compute_ca_key_path.write_bytes(
        unrelated_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    with pytest.raises(identity.IdentityError, match="invalid"):
        identity.ensure_compute_ca()


def test_issue_node_certificate_has_client_auth_and_stable_fingerprint(pki_dir: Path) -> None:
    issued = identity.issue_node_certificate(
        _csr(),
        node_id="018f-node-a",
        expected_common_name="Node A",
    )
    certificate = x509.load_pem_x509_certificate(issued.certificate_pem)

    assert issued.fingerprint == identity.certificate_fingerprint(issued.certificate_pem)
    assert certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "018f-node-a"
    assert certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value == x509.ExtendedKeyUsage(
        [ExtendedKeyUsageOID.CLIENT_AUTH]
    )
    assert certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False
    key_usage = certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    assert key_usage.digital_signature is True
    assert key_usage.key_cert_sign is False


@pytest.mark.parametrize(
    ("csr_pem", "message"),
    [
        (b"not a csr", "CSR"),
        (b"x" * 20000, "CSR"),
        (_csr("Wrong Node"), "common name"),
    ],
)
def test_issue_node_certificate_rejects_invalid_csr(pki_dir: Path, csr_pem: bytes, message: str) -> None:
    with pytest.raises(identity.IdentityError, match=message):
        identity.issue_node_certificate(
            csr_pem,
            node_id="018f-node-a",
            expected_common_name="Node A",
        )
