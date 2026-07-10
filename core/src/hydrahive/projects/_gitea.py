from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx

from hydrahive.projects._git_ops import _runx, set_named_remote
from hydrahive.settings import settings

logger = logging.getLogger(__name__)

REMOTE_NAME = "gitea"
_CONFIG_FILE = "gitea_config.json"
_REPO_RE = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True)
class GiteaConfig:
    url: str
    token: str
    admin_user: str


def _is_local_gitea_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and host in {"127.0.0.1", "localhost", "::1"}


def load_config(config_file: Path | None = None) -> GiteaConfig | None:
    """Liest die lokale Gitea-Systemkonfiguration ohne Secrets zu loggen.

    Die Installer-Extension schreibt `/etc/hydrahive2/gitea_config.json`. Für den
    Standardflow akzeptieren wir bewusst nur lokale URLs, damit kein UI-/API-Input
    als beliebiger Git-Server missbraucht werden kann.
    """
    path = config_file or (settings.config_dir / _CONFIG_FILE)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("Gitea-Konfiguration nicht lesbar: %s", path)
        return None
    url = str(raw.get("url") or "").rstrip("/")
    token = str(raw.get("token") or "")
    admin_user = str(raw.get("admin_user") or "hydrahive")
    if not url or not token or not _is_local_gitea_url(url):
        return None
    return GiteaConfig(url=url, token=token, admin_user=admin_user)


def repo_name_for(project_id: str, repo_name: str) -> str:
    project_part = _REPO_RE.sub("-", project_id.lower()).strip("-._")[:12] or "project"
    repo_part = _REPO_RE.sub("-", repo_name.lower()).strip("-._")[:40] or "repo"
    return f"hh-{project_part}-{repo_part}"[:60].strip("-._")


def _headers(cfg: GiteaConfig) -> dict[str, str]:
    return {"Authorization": f"token {cfg.token}", "Accept": "application/json"}


def _remote_url(cfg: GiteaConfig, owner: str, repo_name: str) -> str:
    return f"{cfg.url}/{quote(owner)}/{quote(repo_name)}.git"


def _repo_api_url(cfg: GiteaConfig, owner: str, repo_name: str) -> str:
    return f"{cfg.url}/api/v1/repos/{quote(owner)}/{quote(repo_name)}"


def remote_url(repo_path: Path) -> str | None:
    ok, out, _ = _runx(repo_path, "remote", "get-url", REMOTE_NAME)
    return out if ok and out else None


def status(project_id: str, repo_name: str, repo_path: Path) -> dict:
    cfg = load_config()
    wanted_name = repo_name_for(project_id, repo_name)
    current_remote = remote_url(repo_path)
    out = {
        "configured": cfg is not None,
        "remote_name": REMOTE_NAME,
        "remote_present": current_remote is not None,
        "remote_url": current_remote,
        "repo_name": wanted_name,
        "owner": cfg.admin_user if cfg else None,
        "repo_exists": False,
        "web_url": None,
    }
    if not cfg:
        return out
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(_repo_api_url(cfg, cfg.admin_user, wanted_name), headers=_headers(cfg))
        if r.status_code == 200:
            data = r.json()
            out["repo_exists"] = True
            out["web_url"] = data.get("html_url") or f"{cfg.url}/{cfg.admin_user}/{wanted_name}"
    except httpx.HTTPError:
        logger.warning("Gitea-Status nicht abrufbar")
    return out


def create_repo_and_remote(project_id: str, repo_name: str, repo_path: Path) -> tuple[bool, str, dict]:
    cfg = load_config()
    if not cfg:
        return False, "gitea_not_configured", {}
    target_name = repo_name_for(project_id, repo_name)
    payload = {"name": target_name, "private": True, "auto_init": False}
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(f"{cfg.url}/api/v1/user/repos", headers=_headers(cfg), json=payload)
    except httpx.HTTPError:
        return False, "gitea_unreachable", {}
    if r.status_code not in {201, 409}:
        return False, "gitea_create_failed", {"status_code": r.status_code}
    url = _remote_url(cfg, cfg.admin_user, target_name)
    ok, err = set_named_remote(repo_path, REMOTE_NAME, url)
    if not ok:
        return False, err or "git_failed", {}
    return True, "", status(project_id, repo_name, repo_path)


def _branch(repo_path: Path) -> str:
    ok, out, _ = _runx(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    return out if ok and out else "HEAD"


def _git_env() -> dict[str, str]:
    return {"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}


def push_remote(repo_path: Path) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg:
        return False, "gitea_not_configured"
    if not remote_url(repo_path):
        return False, "no_remote"
    target = _branch(repo_path)
    # Token nicht im Remote speichern; nur für diesen Git-Aufruf als HTTP-Header.
    ok, _, err = _runx(
        repo_path,
        "-c", f"http.extraHeader=Authorization: token {cfg.token}",
        "push", "--set-upstream", REMOTE_NAME, target,
        env=_git_env(), timeout=120,
    )
    return ok, err


def pull_remote(repo_path: Path) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg:
        return False, "gitea_not_configured"
    if not remote_url(repo_path):
        return False, "no_remote"
    target = _branch(repo_path)
    ok, _, err = _runx(
        repo_path,
        "-c", f"http.extraHeader=Authorization: token {cfg.token}",
        "pull", REMOTE_NAME, target,
        env=_git_env(), timeout=120,
    )
    return ok, err
