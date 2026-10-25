"""update.sh: Git-Schritt verwirft nichts still und springt nie auf einen fremden Branch.

Task cabd0df1, docs/specs/update-git-sicher.md. Vorher: scheiterte `pull --ff-only`
(z. B. weil `npm install` die package-lock.json umschrieb), folgte `reset --hard
origin/main` – lokale Änderungen weg, Feature-Branch auf main.

Getestet mit echten Git-Repos im tmp-Ordner: ein Bare-Repo spielt GitHub, ein
Klon spielt den Server. Keine Netzwerke, kein root.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "installer" / "lib" / "git-update.sh"
UPDATE = REPO_ROOT / "installer" / "update.sh"
LOCK = "frontend/package-lock.json"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                               "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin", "HOME": str(cwd)}).stdout.strip()


def commit(cwd: Path, name: str, text: str, msg: str) -> str:
    p = cwd / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", msg)
    return git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def repos(tmp_path: Path):
    """origin (bare) + dev (zum Pushen) + server (Klon, wie /opt/hydrahive2)."""
    origin = tmp_path / "origin.git"
    dev = tmp_path / "dev"
    server = tmp_path / "server"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(dev))
    commit(dev, LOCK, '{"lock": 1, "peer": true}\n', "lock")
    commit(dev, "core/a.py", "a = 1\n", "a1")
    git(dev, "push", "-q", "origin", "main")
    git(tmp_path, "clone", "-q", str(origin), str(server))
    return origin, dev, server


def run_update(server: Path) -> subprocess.CompletedProcess[str]:
    """hh_git_update im Server-Repo (ohne sudo; HH_GIT ersetzt den Aufruf als hydrahive)."""
    script = f'set -euo pipefail; log(){{ echo "LOG $*"; }}; err(){{ echo "ERR $*" >&2; exit 1; }}; ' \
             f'HH_GIT="git"; source "{HELPER}"; hh_git_update "{server}"'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(server), "GIT_AUTHOR_NAME": "t",
                               "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def head(cwd: Path) -> str:
    return git(cwd, "rev-parse", "HEAD")


def test_vorspulen(repos) -> None:
    _, dev, server = repos
    new = commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == new


def test_bereits_aktuell(repos) -> None:
    _, _, server = repos
    before = head(server)
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == before


def test_umgeschriebene_lock_wird_zurueckgesetzt_und_vorgespult(repos) -> None:
    _, dev, server = repos
    new = commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    (server / LOCK).write_text('{"lock": 1}\n')          # wie npm install: "peer": true entfernt
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == new
    assert (server / LOCK).read_text() == '{"lock": 1, "peer": true}\n'
    assert git(server, "status", "--porcelain") == ""


def test_andere_geaenderte_datei_bricht_ab_und_bleibt(repos) -> None:
    _, dev, server = repos
    commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    before = head(server)
    (server / "core/a.py").write_text("a = 'lokal'\n")
    r = run_update(server)
    assert r.returncode != 0
    assert "core/a.py" in r.stderr and "nichts verworfen" in r.stderr
    assert (server / "core/a.py").read_text() == "a = 'lokal'\n"
    assert head(server) == before


def test_lokaler_commit_bricht_ab_und_bleibt(repos) -> None:
    _, dev, server = repos
    commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    mine = commit(server, "core/b.py", "b = 1\n", "lokal")
    r = run_update(server)
    assert r.returncode != 0
    assert "lokale Commits" in r.stderr
    assert head(server) == mine


def test_branch_bleibt_branch(repos) -> None:
    _, dev, server = repos
    git(dev, "checkout", "-q", "-b", "feat/x")
    feat = commit(dev, "core/f.py", "f = 1\n", "f1")
    git(dev, "push", "-q", "origin", "feat/x")
    git(dev, "checkout", "-q", "main")
    commit(dev, "core/a.py", "a = 9\n", "main weiter")
    git(dev, "push", "-q", "origin", "main")
    git(server, "fetch", "-q", "origin")
    git(server, "checkout", "-q", "-B", "feat/x", "origin/feat/x")
    git(dev, "checkout", "-q", "feat/x")
    feat2 = commit(dev, "core/f.py", "f = 2\n", "f2")
    git(dev, "push", "-q", "origin", "feat/x")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert git(server, "rev-parse", "--abbrev-ref", "HEAD") == "feat/x"
    assert head(server) == feat2 != feat


def test_branch_ohne_upstream_zieht_gleichnamigen_origin_branch(repos) -> None:
    """deploy-test.sh macht `checkout -B <b> origin/<b>` – ob mit oder ohne Tracking: origin/<b> zählt."""
    _, dev, server = repos
    git(dev, "checkout", "-q", "-b", "feat/y")
    commit(dev, "core/y.py", "y = 1\n", "y1")
    git(dev, "push", "-q", "origin", "feat/y")
    git(server, "fetch", "-q", "origin")
    git(server, "checkout", "-q", "--no-track", "-B", "feat/y", "origin/feat/y")
    y2 = commit(dev, "core/y.py", "y = 2\n", "y2")
    git(dev, "push", "-q", "origin", "feat/y")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == y2


def test_history_rewrite_ohne_eigene_commits_setzt_mit_sicherung_zurueck(repos) -> None:
    _, dev, server = repos
    old = head(server)
    git(dev, "reset", "-q", "--hard", "HEAD~1")
    rewritten = commit(dev, "core/a.py", "a = 'neu geschrieben'\n", "rewrite")
    git(dev, "push", "-q", "-f", "origin", "main")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == rewritten
    tags = git(server, "tag", "--list", "hh-update-vorher-*").splitlines()
    assert len(tags) == 1 and git(server, "rev-parse", tags[0]) == old


def test_history_rewrite_mit_eigenem_commit_bricht_ab(repos) -> None:
    _, dev, server = repos
    mine = commit(server, "core/b.py", "b = 1\n", "lokal")
    git(dev, "reset", "-q", "--hard", "HEAD~1")
    commit(dev, "core/a.py", "a = 'neu'\n", "rewrite")
    git(dev, "push", "-q", "-f", "origin", "main")
    r = run_update(server)
    assert r.returncode != 0
    assert head(server) == mine


def test_detached_head_bricht_ab(repos) -> None:
    _, _, server = repos
    git(server, "checkout", "-q", "--detach")
    r = run_update(server)
    assert r.returncode != 0
    assert "Branch" in r.stderr


def test_fetch_fehler_bricht_ab(repos) -> None:
    origin, _, server = repos
    origin.rename(origin.with_name("weg.git"))
    r = run_update(server)
    assert r.returncode != 0
    assert "Netzwerk oder Zugang" in r.stderr


def test_update_sh_nutzt_den_sicheren_weg() -> None:
    text = UPDATE.read_text()
    assert "reset --hard origin/main" not in text
    assert 'source "$HH_REPO_DIR/installer/lib/git-update.sh"' in text
    assert re.search(r'^hh_git_update "\$HH_REPO_DIR"', text, re.M)
    fe = text[text.index('log "Frontend neu bauen"'):text.index("WA_BRIDGE_DIR=")]
    assert "npm ci --no-fund --no-audit" in fe and "npm install" not in fe


def test_erstinstallation_und_whatsapp_mit_npm_ci() -> None:
    fe = (REPO_ROOT / "installer" / "modules" / "40-frontend.sh").read_text()
    wa = (REPO_ROOT / "installer" / "modules" / "45-whatsapp.sh").read_text()
    upd = UPDATE.read_text()
    assert "npm ci " in fe and "npm install --no-fund" not in fe
    assert "npm ci " in wa and "npm install --cache" not in wa
    wa_upd = upd[upd.index("WA_BRIDGE_DIR="):upd.index('log "Systemd-Timer-Units')]
    assert "npm ci " in wa_upd and "npm install" not in wa_upd
