"""Atomic and retry-safe compute-node enrollment orchestration."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from hydrahive.compute import audit, enrollment, identity
from hydrahive.compute._node_codec import dump_json, row_to_node
from hydrahive.compute.models import ComputeNode
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

RECOVERY_WINDOW_MINUTES = 10


@dataclass(frozen=True)
class EnrollmentResult:
    node: ComputeNode
    certificate_pem: str
    ca_certificate_pem: str
    certificate_fingerprint: str
    certificate_expires_at: str


def _token_row(conn: sqlite3.Connection, digest: str):
    return conn.execute(
        """SELECT token_id, requested_name, expires_at, consumed_at
           FROM compute_enrollment_tokens WHERE token_hmac = ?""",
        (digest,),
    ).fetchone()


def _recovered_result(
    conn: sqlite3.Connection,
    *,
    token_id: str,
    csr_sha256: str,
) -> EnrollmentResult | None:
    row = conn.execute(
        """SELECT r.csr_sha256, r.certificate_pem, r.certificate_expires_at,
                  r.recovery_until, n.*
           FROM compute_enrollment_results r
           JOIN compute_nodes n ON n.node_id = r.node_id
           WHERE r.token_id = ?""",
        (token_id,),
    ).fetchone()
    if row is None:
        return None
    if row["recovery_until"] <= now_iso() or row["csr_sha256"] != csr_sha256:
        raise enrollment.EnrollmentError()
    ca = identity.ensure_compute_ca()
    node = row_to_node(row)
    return EnrollmentResult(
        node=node,
        certificate_pem=row["certificate_pem"],
        ca_certificate_pem=ca.certificate_pem.decode("ascii"),
        certificate_fingerprint=node.certificate_fingerprint or "",
        certificate_expires_at=row["certificate_expires_at"],
    )


def enroll_node(
    *,
    token: str,
    csr_pem: str,
    protocol_version: int,
    agent_version: str,
    capabilities: dict[str, object],
    resources: dict[str, object],
) -> EnrollmentResult:
    digest = enrollment.token_digest(token)
    csr_bytes = csr_pem.encode("utf-8")
    csr_sha256 = hashlib.sha256(csr_bytes).hexdigest()
    timestamp = now_iso()
    with db() as conn:
        token_row = _token_row(conn, digest)
        if token_row is None:
            raise enrollment.EnrollmentError()
        if token_row["consumed_at"] is not None:
            recovered = _recovered_result(conn, token_id=token_row["token_id"], csr_sha256=csr_sha256)
            if recovered is None:
                raise enrollment.EnrollmentError()
            return recovered
        if token_row["expires_at"] <= timestamp:
            raise enrollment.EnrollmentError()
        requested_name = token_row["requested_name"]

    if protocol_version != 1:
        raise enrollment.EnrollmentError()
    if not agent_version or len(agent_version) > 64 or not agent_version.isprintable():
        raise enrollment.EnrollmentError()
    capabilities_json = dump_json(capabilities, "capabilities")
    resources_json = dump_json(resources, "resources")
    node_id = uuid7()
    issued = identity.issue_node_certificate(
        csr_bytes,
        node_id=node_id,
        expected_common_name=requested_name,
    )

    with db(immediate=True) as conn:
        token_row = _token_row(conn, digest)
        if token_row is None:
            raise enrollment.EnrollmentError()
        if token_row["consumed_at"] is not None:
            recovered = _recovered_result(conn, token_id=token_row["token_id"], csr_sha256=csr_sha256)
            if recovered is None:
                raise enrollment.EnrollmentError()
            return recovered
        if token_row["expires_at"] <= now_iso():
            raise enrollment.EnrollmentError()
        timestamp = now_iso()
        recovery_until = (
            (datetime.now(UTC) + timedelta(minutes=RECOVERY_WINDOW_MINUTES)).isoformat().replace("+00:00", "Z")
        )
        conn.execute(
            """INSERT INTO compute_nodes (
                   node_id, name, kind, status, certificate_fingerprint,
                   protocol_version, agent_version, capabilities_json,
                   resources_json, labels_json, created_at, updated_at
               ) VALUES (?, ?, 'agent', 'pending', ?, ?, ?, ?, ?, '{}', ?, ?)""",
            (
                node_id,
                requested_name,
                issued.fingerprint,
                protocol_version,
                agent_version,
                capabilities_json,
                resources_json,
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            "UPDATE compute_enrollment_tokens SET consumed_at = ? WHERE token_id = ? AND consumed_at IS NULL",
            (timestamp, token_row["token_id"]),
        )
        conn.execute(
            """INSERT INTO compute_enrollment_results
                   (token_id, csr_sha256, node_id, certificate_pem,
                    certificate_expires_at, recovery_until, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                token_row["token_id"],
                csr_sha256,
                node_id,
                issued.certificate_pem.decode("ascii"),
                issued.expires_at,
                recovery_until,
                timestamp,
            ),
        )
        audit.record_in_connection(
            conn,
            actor=f"enrollment:{token_row['token_id']}",
            action="node.enrolled",
            node_id=node_id,
            details={"agent_version": agent_version, "protocol_version": protocol_version},
        )
        node = row_to_node(conn.execute("SELECT * FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone())
    return EnrollmentResult(
        node=node,
        certificate_pem=issued.certificate_pem.decode("ascii"),
        ca_certificate_pem=issued.ca_certificate_pem.decode("ascii"),
        certificate_fingerprint=issued.fingerprint,
        certificate_expires_at=issued.expires_at,
    )
