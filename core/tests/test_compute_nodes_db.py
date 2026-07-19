from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hydrahive.compute import db as node_db
from hydrahive.compute.models import MAX_NODE_JSON_BYTES, ComputeNode
from hydrahive.db.connection import init_db
from hydrahive.settings import settings


@pytest.fixture
def compute_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database = tmp_path / "compute.db"
    monkeypatch.setattr(settings, "sessions_db", database, raising=False)
    init_db()
    return database


def test_node_registry_create_get_list_and_json_round_trip(compute_db: Path) -> None:
    created = node_db.create_node(
        node_id="node-a",
        name="Compute A",
        kind="agent",
        status="pending",
        protocol_version=1,
        capabilities={"instances": ["container"]},
        resources={"cpu_cores": 8},
        labels={"zone": "lab"},
    )

    assert isinstance(created, ComputeNode)
    assert node_db.get_node("node-a") == created
    assert [node.node_id for node in node_db.list_nodes()] == ["local", "node-a"]
    assert created.capabilities == {"instances": ["container"]}
    assert created.resources == {"cpu_cores": 8}
    assert created.labels == {"zone": "lab"}


def test_node_registry_enforces_unique_names_and_reserved_local_identity(compute_db: Path) -> None:
    node_db.create_node(node_id="node-a", name="Compute A")

    with pytest.raises(sqlite3.IntegrityError):
        node_db.create_node(node_id="node-b", name="Compute A")
    with pytest.raises(ValueError, match="reserved"):
        node_db.create_node(node_id="local", name="Not Local")
    with pytest.raises(ValueError, match="reserved"):
        node_db.create_node(node_id="node-local", name="Another Local", kind="local")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"status": "unknown"}, "status"),
        ({"kind": "unknown"}, "kind"),
        ({"protocol_version": 0}, "protocol_version"),
        ({"name": ""}, "name"),
    ],
)
def test_node_registry_validates_model_bounds(compute_db: Path, kwargs: dict[str, object], message: str) -> None:
    values = {"node_id": "node-a", "name": "Compute A"} | kwargs
    with pytest.raises(ValueError, match=message):
        node_db.create_node(**values)  # type: ignore[arg-type]


def test_node_registry_updates_fields_and_validates_status_transitions(compute_db: Path) -> None:
    node_db.create_node(node_id="node-a", name="Compute A")

    updated = node_db.update_node(
        "node-a",
        name="Compute Alpha",
        status="online",
        agent_version="1.2.3",
        capabilities={"instances": ["container", "vm"]},
    )
    assert updated is not None
    assert updated.name == "Compute Alpha"
    assert updated.status == "online"
    assert updated.agent_version == "1.2.3"

    with pytest.raises(ValueError, match="transition"):
        node_db.update_node("node-a", status="pending")


def test_node_registry_rejects_invalid_and_oversized_json(compute_db: Path) -> None:
    with pytest.raises(ValueError, match="JSON"):
        node_db.create_node(node_id="node-a", name="Compute A", labels={"bad": object()})

    with pytest.raises(ValueError, match="too large"):
        node_db.create_node(
            node_id="node-b",
            name="Compute B",
            resources={"payload": "x" * MAX_NODE_JSON_BYTES},
        )


def test_node_registry_persists_revoke_and_delete(compute_db: Path) -> None:
    node_db.create_node(node_id="node-a", name="Compute A")
    revoked = node_db.revoke_node("node-a")
    assert revoked is not None
    assert revoked.status == "revoked"
    assert revoked.revoked_at is not None
    with pytest.raises(ValueError, match="transition"):
        node_db.update_node("node-a", status="online")

    node_db.create_node(node_id="node-b", name="Compute B")
    node_db.delete_node("node-b")
    assert node_db.get_node("node-b") is None


def test_local_node_cannot_be_deleted_or_revoked(compute_db: Path) -> None:
    with pytest.raises(ValueError, match="local"):
        node_db.delete_node("local")
    with pytest.raises(ValueError, match="local"):
        node_db.revoke_node("local")

    assert node_db.get_node("local") is not None
