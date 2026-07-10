from __future__ import annotations

import json


class _Resp:
    def __init__(self, status_code: int, data: dict | None = None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class _FakeClient:
    posts: list[tuple[str, dict]] = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers=None, json=None):
        self.posts.append((url, json or {}))
        return _Resp(201, {"html_url": "http://127.0.0.1:3000/hydrahive/repo"})

    def get(self, url, headers=None):
        return _Resp(200, {"html_url": "http://127.0.0.1:3000/hydrahive/repo"})


def test_gitea_load_config_accepts_only_local_urls(mod_env):
    from hydrahive.projects import _gitea

    cfg_file = mod_env / "data" / "cfg.json"
    cfg_file.write_text(json.dumps({"url": "http://127.0.0.1:3000", "token": "secret", "admin_user": "hydrahive"}))
    cfg = _gitea.load_config(cfg_file)
    assert cfg is not None
    assert cfg.url == "http://127.0.0.1:3000"
    assert cfg.admin_user == "hydrahive"

    cfg_file.write_text(json.dumps({"url": "https://evil.example", "token": "secret", "admin_user": "hydrahive"}))
    assert _gitea.load_config(cfg_file) is None


def test_gitea_repo_name_is_deterministic_and_safe():
    from hydrahive.projects import _gitea

    assert _gitea.repo_name_for("019ABC_def", "My Repo!!") == "hh-019abc_def-my-repo"


def test_gitea_create_repo_sets_named_remote_without_returning_token(mod_env, monkeypatch, tmp_path):
    from hydrahive.settings import settings
    from hydrahive.projects import _gitea

    monkeypatch.setattr(settings, "config_dir", mod_env / "config", raising=False)
    settings.config_dir.mkdir(exist_ok=True)
    (settings.config_dir / "gitea_config.json").write_text(json.dumps({
        "url": "http://127.0.0.1:3000",
        "token": "secret-token",
        "admin_user": "hydrahive",
    }))
    monkeypatch.setattr(_gitea.httpx, "Client", _FakeClient)
    calls = []

    def fake_set_remote(repo_path, remote_name, url):
        calls.append((remote_name, url))
        return True, ""

    monkeypatch.setattr(_gitea, "set_named_remote", fake_set_remote)
    monkeypatch.setattr(_gitea, "remote_url", lambda repo_path: calls[-1][1] if calls else None)

    ok, err, status = _gitea.create_repo_and_remote("proj-123", "main", tmp_path)

    assert ok is True
    assert err == ""
    assert calls == [("gitea", "http://127.0.0.1:3000/hydrahive/hh-proj-123-main.git")]
    assert status["configured"] is True
    assert "secret-token" not in repr(status)
    assert "secret-token" not in repr(_FakeClient.posts)
