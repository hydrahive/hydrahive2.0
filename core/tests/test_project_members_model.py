"""Tests für die Member-Rollen-Abstraktion (projects/_members_model.py)."""
from __future__ import annotations

from hydrahive.projects import _members_model as mm


class TestNormalize:
    def test_legacy_str_list_becomes_write(self):
        out = mm.normalize_members(["till", "bibs"])
        assert out == [
            {"username": "till", "role": "write"},
            {"username": "bibs", "role": "write"},
        ]

    def test_dict_list_preserved(self):
        raw = [{"username": "till", "role": "read"}]
        assert mm.normalize_members(raw) == [{"username": "till", "role": "read"}]

    def test_mixed_list(self):
        raw = ["till", {"username": "bibs", "role": "admin"}]
        out = mm.normalize_members(raw)
        assert {"username": "till", "role": "write"} in out
        assert {"username": "bibs", "role": "admin"} in out

    def test_unknown_role_falls_back(self):
        raw = [{"username": "x", "role": "superuser"}]
        assert mm.normalize_members(raw) == [{"username": "x", "role": "write"}]

    def test_duplicate_last_wins(self):
        raw = [{"username": "x", "role": "read"}, {"username": "x", "role": "admin"}]
        assert mm.normalize_members(raw) == [{"username": "x", "role": "admin"}]

    def test_garbage_ignored(self):
        assert mm.normalize_members(None) == []
        assert mm.normalize_members("nope") == []
        assert mm.normalize_members([123, {"role": "read"}, {"username": ""}]) == []


class TestRoleOf:
    def test_created_by_is_admin(self):
        p = {"created_by": "boss", "members": []}
        assert mm.role_of(p, "boss") == "admin"

    def test_member_role(self):
        p = {"created_by": "boss", "members": [{"username": "j", "role": "read"}]}
        assert mm.role_of(p, "j") == "read"

    def test_legacy_member_is_write(self):
        p = {"created_by": "boss", "members": ["j"]}
        assert mm.role_of(p, "j") == "write"

    def test_non_member_none(self):
        p = {"created_by": "boss", "members": []}
        assert mm.role_of(p, "stranger") is None

    def test_empty_username_none(self):
        assert mm.role_of({"created_by": "boss"}, "") is None


class TestHasAtLeast:
    def test_ranking(self):
        assert mm.has_at_least("admin", "read")
        assert mm.has_at_least("admin", "write")
        assert mm.has_at_least("admin", "admin")
        assert mm.has_at_least("write", "read")
        assert mm.has_at_least("write", "write")
        assert not mm.has_at_least("write", "admin")
        assert mm.has_at_least("read", "read")
        assert not mm.has_at_least("read", "write")
        assert not mm.has_at_least("read", "admin")

    def test_none_never_qualifies(self):
        assert not mm.has_at_least(None, "read")


class TestUsernamesAndIsMember:
    def test_usernames_from_dicts(self):
        p = {"members": [{"username": "a", "role": "read"}, {"username": "b", "role": "admin"}]}
        assert mm.usernames(p) == ["a", "b"]

    def test_usernames_from_legacy(self):
        assert mm.usernames({"members": ["a", "b"]}) == ["a", "b"]

    def test_is_member(self):
        p = {"created_by": "boss", "members": [{"username": "a", "role": "read"}]}
        assert mm.is_member(p, "a")
        assert mm.is_member(p, "boss")
        assert not mm.is_member(p, "x")
