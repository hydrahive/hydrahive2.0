from __future__ import annotations

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from hydrahive.api.middleware import inbound_ratelimit
from hydrahive.compute import audit
from tests.conftest import error_code


def _csr(common_name: str) -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
        .decode("ascii")
    )


def test_full_node_enrollment_approval_disable_enable_and_revoke(client, admin_headers) -> None:
    inbound_ratelimit.reset()
    token_response = client.post(
        "/api/compute/enrollments",
        headers=admin_headers,
        json={"requested_name": "API Flow Node", "ttl_seconds": 300},
    )
    assert token_response.status_code == 201
    token = token_response.json()["token"]

    csr_pem = _csr("API Flow Node")
    enrollment_payload = {
        "token": token,
        "csr_pem": csr_pem,
        "protocol_version": 1,
        "agent_version": "1.0.0",
        "capabilities": {"instances": ["container", "vm"]},
        "resources": {"cpu_cores": 8},
    }
    enrolled = client.post("/api/compute/agent/enroll", json=enrollment_payload)
    assert enrolled.status_code == 201
    result = enrolled.json()
    node_id = result["node"]["node_id"]
    fingerprint = result["certificate_fingerprint"]
    assert result["node"]["status"] == "pending"
    assert x509.load_pem_x509_certificate(result["certificate_pem"].encode("ascii"))

    recovered = client.post("/api/compute/agent/enroll", json=enrollment_payload)
    assert recovered.status_code == 201
    assert recovered.json()["node"]["node_id"] == node_id
    assert recovered.json()["certificate_pem"] == result["certificate_pem"]

    changed_csr = enrollment_payload | {"csr_pem": _csr("API Flow Node")}
    reused = client.post("/api/compute/agent/enroll", json=changed_csr)
    assert reused.status_code == 400
    assert error_code(reused) == "compute_enrollment_invalid"

    mismatch = client.post(
        f"/api/compute/nodes/{node_id}/approve",
        headers=admin_headers,
        json={"certificate_fingerprint": "00" * 32},
    )
    assert mismatch.status_code == 409
    assert error_code(mismatch) == "compute_fingerprint_mismatch"

    approved = client.post(
        f"/api/compute/nodes/{node_id}/approve",
        headers=admin_headers,
        json={"certificate_fingerprint": fingerprint},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "offline"

    disabled = client.post(f"/api/compute/nodes/{node_id}/disable", headers=admin_headers)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    enabled = client.post(f"/api/compute/nodes/{node_id}/enable", headers=admin_headers)
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "online"
    revoked = client.delete(f"/api/compute/nodes/{node_id}", headers=admin_headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    actions = {record["action"] for record in audit.list_records(node_id=node_id)}
    assert {"node.enrolled", "node.approved", "node.disabled", "node.online", "node.revoked"} <= actions


def test_agent_enrollment_rejects_oversized_body_before_json_parsing(client) -> None:
    inbound_ratelimit.reset()
    oversized = b"{" + b"x" * (97 * 1024)

    response = client.post(
        "/api/compute/agent/enroll",
        content=oversized,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert error_code(response) == "compute_enrollment_body_too_large"


def test_agent_enrollment_is_rate_limited(client, monkeypatch) -> None:
    from hydrahive.api.routes import compute_agent

    inbound_ratelimit.reset()
    monkeypatch.setattr(compute_agent, "ENROLL_IP_RATE_LIMIT", 2)
    monkeypatch.setattr(compute_agent, "ENROLL_TOKEN_RATE_LIMIT", 10)
    payload = {"token": "x" * 43, "csr_pem": _csr("Rate Node"), "agent_version": "1.0.0"}

    assert client.post("/api/compute/agent/enroll", json=payload).status_code == 400
    assert client.post("/api/compute/agent/enroll", json=payload).status_code == 400
    limited = client.post("/api/compute/agent/enroll", json=payload)
    assert limited.status_code == 429
    assert error_code(limited) == "rate_limited"
