"""Task 3223371d: Projekt-API gibt keine Secrets aus, PATCH speichert die
UI-Felder, MCP-/Plugin-Listen des Projekts schränken die Tools ein."""
from __future__ import annotations

import json
import tarfile

import pytest

_WEBHOOK = "webhook-SECRET-value-1234567890"
_GIT_TOKEN = "ghp_REPO-token-value-1234567890"
_LEGACY_KEY = "sk-legacy-project-key-1234567890"


def _create(client, admin_headers, members=None) -> str:
    body = {"name": "Secret-Projekt", "llm_model": "test/model", "members": members or []}
    r = client.post("/api/projects", headers=admin_headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _plant_secrets(pid: str) -> None:
    from hydrahive.projects import config as project_config
    project_config.update(pid, webhook_secret=_WEBHOOK, llm_api_key=_LEGACY_KEY,
                          git_repos={"_root": {"git_token": _GIT_TOKEN}, "extra": {}})


def _assert_clean(payload) -> None:
    text = json.dumps(payload)
    for secret in (_WEBHOOK, _GIT_TOKEN, _LEGACY_KEY):
        assert secret not in text
    for key in ('"webhook_secret"', '"git_token"', '"llm_api_key"'):
        assert key not in text


class TestNoSecretsInResponses:
    def test_create_response(self, client, admin_headers):
        r = client.post("/api/projects", headers=admin_headers,
                        json={"name": "Neu", "llm_model": "test/model"})
        assert r.status_code == 201
        assert "webhook_secret" not in r.json() and r.json()["has_webhook_secret"] is True

    def test_get_as_read_member(self, client, admin_headers, auth_headers):
        pid = _create(client, admin_headers, members=[{"username": "testuser", "role": "read"}])
        _plant_secrets(pid)
        r = client.get(f"/api/projects/{pid}", headers=auth_headers)
        assert r.status_code == 200
        _assert_clean(r.json())
        assert r.json()["has_webhook_secret"] is True
        assert r.json()["git_repos"] == {"_root": {"has_token": True}, "extra": {"has_token": False}}

    def test_list_as_member_and_admin(self, client, admin_headers, auth_headers):
        pid = _create(client, admin_headers, members=["testuser"])
        _plant_secrets(pid)
        for headers in (auth_headers, admin_headers):
            r = client.get("/api/projects", headers=headers)
            assert r.status_code == 200
            assert any(p["id"] == pid for p in r.json())
            _assert_clean(r.json())

    def test_patch_and_member_routes(self, client, admin_headers):
        pid = _create(client, admin_headers)
        _plant_secrets(pid)
        _assert_clean(client.patch(f"/api/projects/{pid}", headers=admin_headers,
                                   json={"description": "x"}).json())
        _assert_clean(client.post(f"/api/projects/{pid}/members/testuser",
                                  headers=admin_headers, json={"role": "read"}).json())
        _assert_clean(client.patch(f"/api/projects/{pid}/members/testuser",
                                   headers=admin_headers, json={"role": "write"}).json())
        _assert_clean(client.delete(f"/api/projects/{pid}/members/testuser",
                                    headers=admin_headers).json())

    def test_secrets_stay_stored(self, client, admin_headers):
        """Nur die Ausgabe ist gefiltert — Webhook/Git-Push brauchen die Werte."""
        from hydrahive.projects import config as project_config
        pid = _create(client, admin_headers)
        _plant_secrets(pid)
        client.patch(f"/api/projects/{pid}", headers=admin_headers, json={"notes": "n"})
        stored = project_config.get(pid)
        assert stored["webhook_secret"] == _WEBHOOK
        assert stored["git_repos"]["_root"]["git_token"] == _GIT_TOKEN


class TestPatchFields:
    def test_notes_tags_overrides_are_saved(self, client, admin_headers):
        pid = _create(client, admin_headers)
        body = {"notes": "Notiz", "tags": ["a", "b"], "mcp_server_ids": ["srv-1"],
                "allowed_plugins": ["git-stats"]}
        r = client.patch(f"/api/projects/{pid}", headers=admin_headers, json=body)
        assert r.status_code == 200, r.text
        got = client.get(f"/api/projects/{pid}", headers=admin_headers).json()
        for k, v in body.items():
            assert got[k] == v

    def test_llm_api_key_not_accepted(self, client, admin_headers):
        from hydrahive.projects import config as project_config
        pid = _create(client, admin_headers)
        client.patch(f"/api/projects/{pid}", headers=admin_headers, json={"llm_api_key": "sk-neu"})
        assert not project_config.get(pid).get("llm_api_key")

    @pytest.mark.parametrize("field,value", [
        ("mcp_server_ids", ["bad id"]), ("allowed_plugins", ["../x"]), ("tags", [""]),
    ])
    def test_invalid_ids_rejected(self, client, admin_headers, field, value):
        pid = _create(client, admin_headers)
        r = client.patch(f"/api/projects/{pid}", headers=admin_headers, json={field: value})
        assert r.status_code == 422

    def test_audit_does_not_store_notes_text(self, client, admin_headers):
        pid = _create(client, admin_headers)
        client.patch(f"/api/projects/{pid}", headers=admin_headers, json={"notes": "geheime Notiz"})
        entries = client.get(f"/api/projects/{pid}/audit", headers=admin_headers).json()["entries"]
        assert "geheime Notiz" not in json.dumps(entries)


class TestToolScope:
    def test_empty_lists_change_nothing(self):
        from hydrahive.runner._project_tool_scope import scope_tools
        tools = ["shell_exec", "plugin__git-stats__git_commits"]
        assert scope_tools({"mcp_server_ids": [], "allowed_plugins": []}, tools, ["m1"]) == (tools, ["m1"])
        assert scope_tools(None, tools, ["m1"]) == (tools, ["m1"])

    def test_only_restricts_never_extends(self):
        from hydrahive.runner._project_tool_scope import scope_tools
        proj = {"mcp_server_ids": ["m1", "m9"], "allowed_plugins": ["git-stats", "extra"]}
        tools = ["shell_exec", "plugin__git-stats__git_commits", "plugin__http-tester__request"]
        local, mcp = scope_tools(proj, tools, ["m1", "m2"])
        assert local == ["shell_exec", "plugin__git-stats__git_commits"]
        assert mcp == ["m1"]


def test_member_backup_has_no_owner_secrets(client, admin_headers):
    from hydrahive.backup.user_archive import create_user_archive
    from hydrahive.settings import settings
    pid = _create(client, admin_headers, members=["testuser"])
    _plant_secrets(pid)
    archive = create_user_archive("testuser", settings.data_dir / "bk-test")
    with tarfile.open(archive, "r:gz") as tar:
        cfg = tar.extractfile(f"projects/{pid}/config.json").read().decode()
    _assert_clean(json.loads(cfg))
    assert json.loads(cfg)["id"] == pid
