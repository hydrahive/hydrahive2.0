"""Gruppen-Speicher (Spec access-groups §6, Plan Task 1.2)."""
from __future__ import annotations

import pytest

from hydrahive.access import store
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


def test_create_and_get_group(client):
    g = store.create_group("Familie-A", "Haushalt", actor_id="admin-id")
    assert g["name"] == "Familie-A" and g["description"] == "Haushalt"
    assert store.get_group(g["id"])["name"] == "Familie-A"


def test_duplicate_group_name_rejected(client):
    store.create_group("Doppelt", "", actor_id="admin-id")
    with pytest.raises(store.GroupExists):
        store.create_group("Doppelt", "", actor_id="admin-id")


def test_rename_group(client):
    g = store.create_group("Alt-Name", "", actor_id="admin-id")
    store.update_group(g["id"], name="Neu-Name", description="x", actor_id="admin-id")
    assert store.get_group(g["id"])["name"] == "Neu-Name"


def test_update_unknown_group_raises(client):
    with pytest.raises(store.GroupNotFound):
        store.update_group("gibt-es-nicht", name="x", actor_id="admin-id")


def test_add_member_is_idempotent(client):
    g = store.create_group("Idem", "", actor_id="admin-id")
    store.add_member(g["id"], "u-1", actor_id="admin-id")
    store.add_member(g["id"], "u-1", actor_id="admin-id")
    assert store.members_of(g["id"]) == ["u-1"]


def test_remove_member(client):
    g = store.create_group("Entf", "", actor_id="admin-id")
    store.add_member(g["id"], "u-1", actor_id="admin-id")
    store.add_member(g["id"], "u-2", actor_id="admin-id")
    store.remove_member(g["id"], "u-1", actor_id="admin-id")
    assert store.members_of(g["id"]) == ["u-2"]


def test_groups_of_user(client):
    a = store.create_group("GA", "", actor_id="admin-id")
    b = store.create_group("GB", "", actor_id="admin-id")
    store.create_group("GC", "", actor_id="admin-id")
    store.add_member(a["id"], "u-x", actor_id="admin-id")
    store.add_member(b["id"], "u-x", actor_id="admin-id")
    assert set(store.groups_of("u-x")) == {a["id"], b["id"]}


def test_delete_group_removes_members(client):
    g = store.create_group("Weg", "", actor_id="admin-id")
    store.add_member(g["id"], "u-del", actor_id="admin-id")
    store.delete_group(g["id"], actor_id="admin-id")
    assert store.get_group(g["id"]) is None
    assert g["id"] not in store.groups_of("u-del")


def test_group_changes_are_audited(client):
    g = store.create_group("Audit-G", "", actor_id="admin-id")
    store.add_member(g["id"], "u-a", actor_id="admin-id")
    actions = [e["action"] for e in store.audit_for(f"group:{g['id']}")]
    assert actions == ["group_create", "group_add_member"]
