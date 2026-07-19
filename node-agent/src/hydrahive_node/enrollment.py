"""HTTPS enrollment client and response verification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from hydrahive_node.storage import AgentIdentity, StatePaths, save_identity


class AgentEnrollmentError(RuntimeError):
    pass


def _verify_signature(certificate: x509.Certificate, issuer: x509.Certificate) -> None:
    public_key = issuer.public_key()
    try:
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                ec.ECDSA(certificate.signature_hash_algorithm),
            )
        elif isinstance(public_key, rsa.RSAPublicKey):
            from cryptography.hazmat.primitives.asymmetric import padding

            public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                padding.PKCS1v15(),
                certificate.signature_hash_algorithm,
            )
        else:
            raise AgentEnrollmentError("unsupported compute CA key")
    except ValueError as exc:
        raise AgentEnrollmentError("node certificate signature is invalid") from exc


def _validate_response(data: dict, private_key: ec.EllipticCurvePrivateKey) -> AgentIdentity:
    try:
        node = data["node"]
        node_id = node["node_id"]
        certificate_pem = data["certificate_pem"].encode("ascii")
        ca_pem = data["ca_certificate_pem"].encode("ascii")
        fingerprint = data["certificate_fingerprint"]
        expires_at = data["certificate_expires_at"]
        certificate = x509.load_pem_x509_certificate(certificate_pem)
        ca_certificate = x509.load_pem_x509_certificate(ca_pem)
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise AgentEnrollmentError("enrollment response is invalid") from exc
    own_public = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    issued_public = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if own_public != issued_public or certificate.issuer != ca_certificate.subject:
        raise AgentEnrollmentError("enrollment certificate does not match this agent")
    _verify_signature(certificate, ca_certificate)
    actual_fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    if actual_fingerprint != fingerprint:
        raise AgentEnrollmentError("enrollment fingerprint mismatch")
    usages = certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    if ExtendedKeyUsageOID.CLIENT_AUTH not in usages:
        raise AgentEnrollmentError("enrollment certificate lacks client authentication")
    sans = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if f"urn:hydrahive:node:{node_id}" not in sans.get_values_for_type(x509.UniformResourceIdentifier):
        raise AgentEnrollmentError("enrollment certificate has wrong node identity")
    if certificate.not_valid_before_utc > datetime.now(UTC) or certificate.not_valid_after_utc <= datetime.now(UTC):
        raise AgentEnrollmentError("enrollment certificate is not currently valid")
    return AgentIdentity(
        server_url="",
        node_id=node_id,
        certificate_fingerprint=fingerprint,
        certificate_expires_at=expires_at,
        protocol_version=1,
    )


def enroll(
    *,
    server_url: str,
    token: str,
    node_name: str,
    paths: StatePaths,
    ca_file: Path | None = None,
    transport: httpx.BaseTransport | None = None,
) -> AgentIdentity:
    server_url = server_url.rstrip("/")
    if not server_url.startswith("https://"):
        raise AgentEnrollmentError("server URL must use HTTPS")
    if not token or len(token) > 128 or not node_name.strip() or len(node_name) > 128:
        raise AgentEnrollmentError("enrollment input is invalid")
    private_key = ec.generate_private_key(ec.SECP256R1())
    csr_pem = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, node_name.strip())]))
        .sign(private_key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
        .decode("ascii")
    )
    verify: bool | str = str(ca_file) if ca_file else True
    try:
        with httpx.Client(verify=verify, timeout=20.0, transport=transport) as client:
            response = client.post(
                f"{server_url}/api/compute/agent/enroll",
                json={
                    "token": token,
                    "csr_pem": csr_pem,
                    "protocol_version": 1,
                    "agent_version": "0.1.0",
                    "capabilities": {},
                    "resources": {},
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AgentEnrollmentError("enrollment request failed") from exc
    identity = _validate_response(data, private_key)
    identity = AgentIdentity(
        server_url=server_url,
        node_id=identity.node_id,
        certificate_fingerprint=identity.certificate_fingerprint,
        certificate_expires_at=identity.certificate_expires_at,
        protocol_version=identity.protocol_version,
    )
    private_key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    save_identity(
        paths,
        identity,
        private_key_pem=private_key_pem,
        certificate_pem=data["certificate_pem"].encode("ascii"),
        ca_certificate_pem=data["ca_certificate_pem"].encode("ascii"),
        server_ca_certificate_pem=ca_file.read_bytes() if ca_file else None,
    )
    return identity
