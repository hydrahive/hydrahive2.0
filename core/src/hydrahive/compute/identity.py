"""Local compute CA and constrained node-client certificate issuance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from hydrahive.compute import _identity_store as identity_store
from hydrahive.compute._node_codec import validate_identity

MAX_CSR_BYTES = 16 * 1024
CA_VALID_DAYS = 3650
NODE_CERT_VALID_DAYS = 90


class IdentityError(ValueError):
    pass


@dataclass(frozen=True)
class ComputeCA:
    certificate_pem: bytes
    fingerprint: str


@dataclass(frozen=True)
class IssuedNodeCertificate:
    certificate_pem: bytes
    ca_certificate_pem: bytes
    fingerprint: str
    expires_at: str


def certificate_fingerprint(certificate_pem: bytes) -> str:
    try:
        certificate = x509.load_pem_x509_certificate(certificate_pem)
    except ValueError as exc:
        raise IdentityError("invalid certificate") from exc
    return certificate.fingerprint(hashes.SHA256()).hex()


def _load_ca_state() -> identity_store.CAState | None:
    try:
        return identity_store.load_ca()
    except ValueError as exc:
        raise IdentityError(str(exc)) from exc


def ensure_compute_ca() -> ComputeCA:
    with identity_store.ca_lock():
        loaded = _load_ca_state()
        if loaded is None:
            key = ec.generate_private_key(ec.SECP384R1())
            now = datetime.now(UTC)
            subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "HydraHive Compute CA")])
            certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(subject)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=CA_VALID_DAYS))
                .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .add_extension(
                    x509.KeyUsage(True, False, False, False, False, True, True, False, False),
                    critical=True,
                )
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                .sign(key, hashes.SHA384())
            )
            key_pem = key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            identity_store.write_ca_pair(key_pem, certificate.public_bytes(serialization.Encoding.PEM))
            loaded = _load_ca_state()
        if loaded is None:  # pragma: no cover - write_ca_pair is validated above
            raise IdentityError("compute CA is unavailable")
        return ComputeCA(
            loaded.certificate_pem,
            certificate_fingerprint(loaded.certificate_pem),
        )


def _validated_csr(csr_pem: bytes, expected_common_name: str) -> x509.CertificateSigningRequest:
    if not isinstance(csr_pem, bytes) or not csr_pem or len(csr_pem) > MAX_CSR_BYTES:
        raise IdentityError("CSR size is invalid")
    try:
        csr = x509.load_pem_x509_csr(csr_pem)
    except ValueError as exc:
        raise IdentityError("CSR is invalid") from exc
    if not csr.is_signature_valid:
        raise IdentityError("CSR signature is invalid")
    names = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if len(names) != 1 or names[0].value != expected_common_name or len(csr.subject) != 1:
        raise IdentityError("CSR common name does not match enrollment")
    if list(csr.extensions):
        raise IdentityError("CSR extensions are not allowed")
    public_key = csr.public_key()
    valid_ec = isinstance(public_key, ec.EllipticCurvePublicKey) and public_key.key_size >= 256
    valid_rsa = isinstance(public_key, rsa.RSAPublicKey) and public_key.key_size >= 2048
    if not valid_ec and not valid_rsa:
        raise IdentityError("CSR public key is not allowed")
    return csr


def issue_node_certificate(
    csr_pem: bytes,
    *,
    node_id: str,
    expected_common_name: str,
) -> IssuedNodeCertificate:
    validate_identity(node_id, expected_common_name)
    csr = _validated_csr(csr_pem, expected_common_name)
    ensure_compute_ca()
    with identity_store.ca_lock():
        loaded = _load_ca_state()
    if loaded is None:  # pragma: no cover - ensure_compute_ca creates it
        raise IdentityError("compute CA is unavailable")
    ca_key = loaded.key
    ca_pem = loaded.certificate_pem
    ca_certificate = loaded.certificate
    now = datetime.now(UTC)
    expires_at = min(now + timedelta(days=NODE_CERT_VALID_DAYS), ca_certificate.not_valid_after_utc)
    if expires_at <= now + timedelta(days=1):
        raise IdentityError("compute CA expires too soon to issue a node certificate")
    public_key = csr.public_key()
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, node_id)]))
        .issuer_name(ca_certificate.subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(expires_at)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=isinstance(public_key, rsa.RSAPublicKey),
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"urn:hydrahive:node:{node_id}")]), False
        )
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), False)
        .sign(ca_key, hashes.SHA384())
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    return IssuedNodeCertificate(
        certificate_pem,
        ca_pem,
        certificate_fingerprint(certificate_pem),
        expires_at.isoformat().replace("+00:00", "Z"),
    )
