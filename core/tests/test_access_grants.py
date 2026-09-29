"""Funktions-Freigaben (Spec access-groups §6/§7, Plan Task 1.3)."""
from __future__ import annotations

import pytest

from hydrahive.access import grants, store
from tests._access_rows import _own_access_rows  # noqa: F401  (autouse)


def test_grant_to_user_and_list(client):
    grants.grant("module.t13a", "user", "u-1", "use", actor_id="admin-id")
    rows = grants.grants_for("module.t13a")
    assert rows == [{"capability": "module.t13a", "subject_type": "user",
                     "subject_id": "u-1", "level": "use"}]


def test_grant_again_changes_level(client):
    grants.grant("module.t13b", "user", "u-1", "use", actor_id="admin-id")
    grants.grant("module.t13b", "user", "u-1", "manage", actor_id="admin-id")
    rows = grants.grants_for("module.t13b")
    assert len(rows) == 1 and rows[0]["level"] == "manage"


def test_everyone_grant_has_empty_subject(client):
    grants.grant("module.t13c", "everyone", "", "use", actor_id="admin-id")
    assert grants.grants_for("module.t13c")[0]["subject_id"] == ""


def test_everyone_with_subject_id_rejected(client):
    with pytest.raises(ValueError):
        grants.grant("module.t13d", "everyone", "u-1", "use", actor_id="admin-id")


def test_user_grant_without_subject_rejected(client):
    with pytest.raises(ValueError):
        grants.grant("module.t13e", "user", "", "use", actor_id="admin-id")


def test_invalid_level_rejected(client):
    with pytest.raises(ValueError):
        grants.grant("module.t13f", "user", "u-1", "owner", actor_id="admin-id")


def test_revoke(client):
    grants.grant("module.t13g", "user", "u-1", "use", actor_id="admin-id")
    grants.revoke("module.t13g", "user", "u-1", actor_id="admin-id")
    assert grants.grants_for("module.t13g") == []


def test_revoke_missing_is_noop_without_audit(client):
    grants.revoke("module.t13h", "user", "u-1", actor_id="admin-id")
    assert store.audit_for("cap:module.t13h") == []


def test_each_change_is_audited_once(client):
    grants.grant("module.t13i", "group", "g-1", "use", actor_id="admin-id")
    grants.grant("module.t13i", "group", "g-1", "manage", actor_id="admin-id")
    grants.revoke("module.t13i", "group", "g-1", actor_id="admin-id")
    log = store.audit_for("cap:module.t13i")
    assert [e["action"] for e in log] == ["grant", "grant", "revoke"]
    assert all(e["actor_id"] == "admin-id" for e in log)
    assert log[1]["detail"] == "group:g-1=manage"


def test_grants_of_subjects(client):
    grants.grant("module.t13j", "user", "u-9", "use", actor_id="admin-id")
    grants.grant("module.t13k", "group", "g-9", "manage", actor_id="admin-id")
    grants.grant("module.t13l", "everyone", "", "use", actor_id="admin-id")
    rows = grants.grants_matching(user_id="u-9", group_ids=["g-9"])
    caps = {(r["capability"], r["level"]) for r in rows}
    assert {("module.t13j", "use"), ("module.t13k", "manage"), ("module.t13l", "use")} <= caps


def test_deleting_group_removes_its_grants(client):
    g = store.create_group("Mit-Freigabe", "", actor_id="admin-id")
    grants.grant("module.t13m", "group", g["id"], "use", actor_id="admin-id")
    store.delete_group(g["id"], actor_id="admin-id")
    assert grants.grants_for("module.t13m") == []
