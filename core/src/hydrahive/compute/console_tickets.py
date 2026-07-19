"""Short-lived, one-time, resource-bound console tickets for remote instances.

A console ticket authorizes a single console session to exactly one remote
resource on one node. Only the HMAC of the opaque secret is persisted; the
plaintext is returned once at issue time. Redemption is single-use and
fail-closed, and revoking a node invalidates all of its pending tickets.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from hydrahive.compute import audit
from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.settings import settings

MIN_TTL_SECONDS = 15
MAX_TTL_SECONDS = 120
DEFAULT_TTL_SECONDS = 30
MAX_TICKET_LENGTH = 128
RESOURCE_KINDS = frozenset({"container", "vm"})
TICKET_RETENTION_HOURS = 6


class ConsoleTicketError(RuntimeError):
    def __init__(self, code: str = "console_ticket_invalid") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class IssuedConsoleTicket:
    ticket_id: str
    ticket: str
    node_id: str
    resource_kind: str
    resource_id: str
    expires_at: str


@dataclass(frozen=True)
class RedeemedConsoleTicket:
    ticket_id: str
    node_id: str
    resource_kind: str
    resource_id: str
    created_by: str


def _validate_ticket_secret(ticket: str) -> str:
    if not isinstance(ticket, str) or not 32 <= len(ticket) <= MAX_TICKET_LENGTH or not ticket.isascii():
        raise ConsoleTicketError()
    return ticket


def ticket_digest(ticket: str) -> str:
    _validate_ticket_secret(ticket)
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        b"hydrahive-compute-console-ticket-v1\0" + ticket.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _require_remote_resource(conn: sqlite3.Connection, node_id: str, resource_kind: str, resource_id: str) -> None:
    if resource_kind not in RESOURCE_KINDS:
        raise ConsoleTicketError()
    if node_id == "local":
        raise ConsoleTicketError("console_ticket_local_not_supported")
    table = "containers" if resource_kind == "container" else "vms"
    id_column = "container_id" if resource_kind == "container" else "vm_id"
    row = conn.execute(
        f"SELECT node_id FROM {table} WHERE {id_column} = ?",  # noqa: S608 - fixed identifiers
        (resource_id,),
    ).fetchone()
    if row is None or row["node_id"] != node_id:
        raise ConsoleTicketError("console_ticket_resource_mismatch")
    node = conn.execute("SELECT kind, status FROM compute_nodes WHERE node_id = ?", (node_id,)).fetchone()
    if node is None or node["kind"] != "agent" or node["status"] not in {"online", "degraded"}:
        raise ConsoleTicketError("console_ticket_node_unavailable")


def issue_ticket(
    *,
    node_id: str,
    resource_kind: str,
    resource_id: str,
    created_by: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> IssuedConsoleTicket:
    if not MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between {MIN_TTL_SECONDS} and {MAX_TTL_SECONDS}")
    ticket = secrets.token_urlsafe(32)
    ticket_id = uuid7()
    expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
    with db(immediate=True) as conn:
        _require_remote_resource(conn, node_id, resource_kind, resource_id)
        retention_cutoff = (
            (datetime.now(UTC) - timedelta(hours=TICKET_RETENTION_HOURS)).isoformat().replace("+00:00", "Z")
        )
        conn.execute("DELETE FROM compute_console_tickets WHERE expires_at < ?", (retention_cutoff,))
        conn.execute(
            """INSERT INTO compute_console_tickets
                   (ticket_id, ticket_hmac, node_id, resource_kind, resource_id,
                    created_by, expires_at, consumed_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
            (
                ticket_id,
                ticket_digest(ticket),
                node_id,
                resource_kind,
                resource_id,
                created_by,
                expires_at,
                now_iso(),
            ),
        )
        audit.record_in_connection(
            conn,
            actor=created_by,
            action="console.ticket_issued",
            node_id=node_id,
            details={"ticket_id": ticket_id, "resource_kind": resource_kind, "resource_id": resource_id},
        )
    return IssuedConsoleTicket(ticket_id, ticket, node_id, resource_kind, resource_id, expires_at)


def redeem_ticket(ticket: str) -> RedeemedConsoleTicket:
    digest = ticket_digest(ticket)
    consumed_at = now_iso()
    with db(immediate=True) as conn:
        row = conn.execute(
            """SELECT ticket_id, node_id, resource_kind, resource_id, created_by
               FROM compute_console_tickets
               WHERE ticket_hmac = ? AND consumed_at IS NULL AND expires_at > ?""",
            (digest, consumed_at),
        ).fetchone()
        if row is None:
            raise ConsoleTicketError()
        # Re-check the node is still usable at redemption time (revocation race).
        node = conn.execute(
            "SELECT kind, status FROM compute_nodes WHERE node_id = ?",
            (row["node_id"],),
        ).fetchone()
        if node is None or node["kind"] != "agent" or node["status"] not in {"online", "degraded"}:
            raise ConsoleTicketError("console_ticket_node_unavailable")
        result = conn.execute(
            """UPDATE compute_console_tickets SET consumed_at = ?
               WHERE ticket_id = ? AND consumed_at IS NULL AND expires_at > ?""",
            (consumed_at, row["ticket_id"], consumed_at),
        )
        if result.rowcount != 1:  # pragma: no cover - BEGIN IMMEDIATE serializes consumers
            raise ConsoleTicketError()
        audit.record_in_connection(
            conn,
            actor=row["created_by"],
            action="console.ticket_redeemed",
            node_id=row["node_id"],
            details={"ticket_id": row["ticket_id"], "resource_kind": row["resource_kind"]},
        )
    return RedeemedConsoleTicket(
        row["ticket_id"],
        row["node_id"],
        row["resource_kind"],
        row["resource_id"],
        row["created_by"],
    )


def revoke_tickets_for_node(node_id: str, *, connection: sqlite3.Connection | None = None) -> int:
    """Consume all pending tickets for a node so they can no longer be redeemed."""
    consumed_at = now_iso()

    def _run(conn: sqlite3.Connection) -> int:
        result = conn.execute(
            "UPDATE compute_console_tickets SET consumed_at = ? WHERE node_id = ? AND consumed_at IS NULL",
            (consumed_at, node_id),
        )
        return result.rowcount

    if connection is not None:
        return _run(connection)
    with db(immediate=True) as conn:
        return _run(conn)
