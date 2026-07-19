from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.compute import console_tickets as tickets
from hydrahive.compute import db as node_db
from hydrahive.containers import db as cdb
from hydrahive.vms import db as vmdb
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def ticket_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "sessions_db", tmp_path / "tickets.db", raising=False)
    init_db()
    node = node_db.create_node(
        node_id="node-remote",
        name="Remote Node",
        certificate_fingerprint="ab" * 32,
        capabilities={"incus": True, "kvm": True, "instance_types": ["container", "vm"]},
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    return node.node_id


def _container(node_id: str):
    return cdb.create(
        owner="admin",
        name="remote-demo",
        image="images:debian/12",
        network_mode="bridged",
        node_id=node_id,
    )


def test_issue_ticket_returns_opaque_secret_and_stores_only_hmac(ticket_db: str) -> None:
    container = _container(ticket_db)
    issued = tickets.issue_ticket(
        node_id=ticket_db,
        resource_kind="container",
        resource_id=container.container_id,
        created_by="admin-id",
    )
    assert len(issued.ticket) >= 32
    # Secret must not be stored in the DB in any recoverable form.
    from hydrahive.db.connection import db

    with db() as conn:
        row = conn.execute(
            "SELECT ticket_hmac FROM compute_console_tickets WHERE ticket_id = ?",
            (issued.ticket_id,),
        ).fetchone()
    assert row["ticket_hmac"] != issued.ticket
    assert issued.ticket not in row["ticket_hmac"]


def test_redeem_is_one_time_and_resource_bound(ticket_db: str) -> None:
    container = _container(ticket_db)
    issued = tickets.issue_ticket(
        node_id=ticket_db,
        resource_kind="container",
        resource_id=container.container_id,
        created_by="admin-id",
    )
    redeemed = tickets.redeem_ticket(issued.ticket)
    assert redeemed.node_id == ticket_db
    assert redeemed.resource_kind == "container"
    assert redeemed.resource_id == container.container_id

    # Second redemption of the same ticket must fail (one-time use).
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.redeem_ticket(issued.ticket)


def test_redeem_rejects_unknown_or_tampered_ticket(ticket_db: str) -> None:
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.redeem_ticket("this-is-not-a-real-ticket-secret-value")


def test_expired_ticket_cannot_be_redeemed(ticket_db: str, monkeypatch) -> None:
    container = _container(ticket_db)
    issued = tickets.issue_ticket(
        node_id=ticket_db,
        resource_kind="container",
        resource_id=container.container_id,
        created_by="admin-id",
        ttl_seconds=tickets.MIN_TTL_SECONDS,
    )
    # Force expiry by rewriting expires_at into the past.
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(
            "UPDATE compute_console_tickets SET expires_at = '2000-01-01T00:00:00Z' WHERE ticket_id = ?",
            (issued.ticket_id,),
        )
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.redeem_ticket(issued.ticket)


def test_issue_rejects_local_resource(ticket_db: str) -> None:
    local = cdb.create(owner="admin", name="local-demo", image="images:debian/12")
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.issue_ticket(
            node_id="local",
            resource_kind="container",
            resource_id=local.container_id,
            created_by="admin-id",
        )


def test_issue_rejects_ttl_out_of_range(ticket_db: str) -> None:
    container = _container(ticket_db)
    with pytest.raises(ValueError):
        tickets.issue_ticket(
            node_id=ticket_db,
            resource_kind="container",
            resource_id=container.container_id,
            created_by="admin-id",
            ttl_seconds=tickets.MAX_TTL_SECONDS + 1,
        )


def test_revoking_node_invalidates_pending_tickets(ticket_db: str) -> None:
    container = _container(ticket_db)
    issued = tickets.issue_ticket(
        node_id=ticket_db,
        resource_kind="container",
        resource_id=container.container_id,
        created_by="admin-id",
    )
    tickets.revoke_tickets_for_node(ticket_db)
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.redeem_ticket(issued.ticket)


def test_node_revocation_invalidates_tickets_end_to_end(ticket_db: str) -> None:
    container = _container(ticket_db)
    issued = tickets.issue_ticket(
        node_id=ticket_db,
        resource_kind="container",
        resource_id=container.container_id,
        created_by="admin-id",
    )
    node_db.revoke_node(ticket_db, actor="admin-id")
    with pytest.raises(tickets.ConsoleTicketError):
        tickets.redeem_ticket(issued.ticket)


def test_console_ticket_api_requires_admin_and_issues_ticket(client, auth_headers, admin_headers) -> None:
    # Unique identifiers keep this test independent of the shared client DB state.
    from hydrahive.db._utils import uuid7

    suffix = uuid7()[:8]
    fingerprint = (suffix * 8)[:64]
    node = node_db.create_node(
        node_id=f"api-node-{suffix}",
        name=f"API Node {suffix}",
        certificate_fingerprint=fingerprint,
        capabilities={"incus": True, "kvm": True, "instance_types": ["container", "vm"]},
    )
    node_db.approve_node(node.node_id, "admin")
    node_db.transition_node_status(node.node_id, "online")
    container = cdb.create(
        owner="admin",
        name=f"apiremote{suffix}",
        image="images:debian/12",
        network_mode="bridged",
        node_id=node.node_id,
    )

    denied = client.post(
        f"/api/compute/nodes/{node.node_id}/console-tickets",
        headers=auth_headers,
        json={"resource_kind": "container", "resource_id": container.container_id},
    )
    assert denied.status_code == 403

    created = client.post(
        f"/api/compute/nodes/{node.node_id}/console-tickets",
        headers=admin_headers,
        json={"resource_kind": "container", "resource_id": container.container_id, "ttl_seconds": 30},
    )
    assert created.status_code == 201
    body = created.json()
    assert len(body["ticket"]) >= 32
    assert body["node_id"] == node.node_id
    assert body["resource_id"] == container.container_id

    redeemed = tickets.redeem_ticket(body["ticket"])
    assert redeemed.resource_id == container.container_id
