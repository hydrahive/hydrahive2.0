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
WA_LOCK = "core/src/hydrahive/communication/whatsapp/bridge/package-lock.json"


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
    commit(dev, WA_LOCK, '{"bridge": 1, "peer": true}\n', "wa-lock")
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


def _code(text: str) -> str:
    """Nur Befehlszeilen – Kommentare dürfen den alten Weg erklären."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_update_sh_nutzt_den_sicheren_weg() -> None:
    text = _code(UPDATE.read_text())
    assert "reset --hard origin/main" not in text
    assert 'source "$HH_REPO_DIR/installer/lib/git-update.sh"' in text
    assert re.search(r'^hh_git_update "\$HH_REPO_DIR"', text, re.M)
    fe = text[text.index('log "Frontend neu bauen"'):text.index("WA_BRIDGE_DIR=")]
    assert "npm ci --no-fund --no-audit" in fe and "npm install" not in fe


def test_erstinstallation_und_whatsapp_mit_npm_ci() -> None:
    fe = _code((REPO_ROOT / "installer" / "modules" / "40-frontend.sh").read_text())
    wa = _code((REPO_ROOT / "installer" / "modules" / "45-whatsapp.sh").read_text())
    upd = _code(UPDATE.read_text())
    assert "npm ci " in fe and "npm install --no-fund" not in fe
    assert "npm ci " in wa and "npm install --cache" not in wa
    wa_upd = upd[upd.index("WA_BRIDGE_DIR="):upd.index('log "Systemd-Timer-Units')]
    assert "npm ci " in wa_upd and "npm install" not in wa_upd


def test_branch_vor_main_springt_nie_auf_main(repos) -> None:
    """Feature-Branch liegt vor main: ein Update auf ihm darf nie nach main wechseln."""
    _, dev, server = repos
    git(dev, "checkout", "-q", "-b", "feat/z")
    z1 = commit(dev, "core/z.py", "z = 1\n", "z1")
    git(dev, "push", "-q", "origin", "feat/z")
    git(server, "fetch", "-q", "origin")
    git(server, "checkout", "-q", "-B", "feat/z", "origin/feat/z")
    main_tip = git(server, "rev-parse", "origin/main")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == z1
    assert git(server, "rev-parse", "--abbrev-ref", "HEAD") == "feat/z"
    assert git(server, "rev-parse", "origin/main") == main_tip      # fremder Stand wird nicht überschrieben


def test_neue_unversionierte_datei_stoert_nicht(repos) -> None:
    """Nicht eingecheckte Dateien (z. B. dist/, Notizen) sind kein Grund zum Abbruch und bleiben."""
    _, dev, server = repos
    new = commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    (server / "notiz.txt").write_text("lokal\n")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == new
    assert (server / "notiz.txt").read_text() == "lokal\n"


def test_vorspulen_ist_kein_reset_unversionierte_kollision_bleibt(repos) -> None:
    """origin bringt eine Datei, die lokal unversioniert schon existiert: Vorspulen bricht ab statt
    sie zu überschreiben (ein Reset würde sie still ersetzen)."""
    _, dev, server = repos
    commit(dev, "core/neu.py", "neu = 'origin'\n", "neu")
    git(dev, "push", "-q", "origin", "main")
    (server / "core/neu.py").write_text("neu = 'lokal'\n")
    r = run_update(server)
    assert r.returncode != 0
    assert (server / "core/neu.py").read_text() == "neu = 'lokal'\n"


def test_origin_nur_weiter_ohne_rewrite_setzt_nicht_zurueck(repos) -> None:
    """Lokal ein eigener Commit, origin ist normal weitergelaufen (kein Rewrite): Abbruch, kein Tag."""
    _, dev, server = repos
    mine = commit(server, "core/b.py", "b = 1\n", "lokal")
    commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    r = run_update(server)
    assert r.returncode != 0
    assert head(server) == mine
    assert git(server, "tag", "--list", "hh-update-vorher-*") == ""


def test_lokal_hinter_altem_origin_und_origin_neu_geschrieben(repos) -> None:
    """Server stand hinter dem alten origin-Stand (alter Fetch), dann Rewrite: trotzdem nur Reset mit Sicherung,
    weil alle lokalen Commits in der alten origin-Geschichte lagen."""
    _, dev, server = repos
    commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    git(server, "fetch", "-q", "origin")          # kennt a2, steht aber noch davor
    old = head(server)
    git(dev, "reset", "-q", "--hard", "HEAD~2")
    rewritten = commit(dev, "core/a.py", "a = 'neu'\n", "rewrite")
    git(dev, "push", "-q", "-f", "origin", "main")
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == rewritten
    assert git(server, "rev-parse", git(server, "tag", "--list", "hh-update-vorher-*")) == old


def test_whatsapp_lock_wird_ebenfalls_zurueckgesetzt(repos) -> None:
    """Befund .4 am 26.10.: Die Bridge-Lock war von npm install umgeschrieben → Update hielt an."""
    _, dev, server = repos
    new = commit(dev, "core/a.py", "a = 2\n", "a2")
    git(dev, "push", "-q", "origin", "main")
    (server / WA_LOCK).write_text('{"bridge": 1}\n')
    (server / LOCK).write_text('{"lock": 1}\n')
    r = run_update(server)
    assert r.returncode == 0, r.stderr
    assert head(server) == new
    assert (server / WA_LOCK).read_text() == '{"bridge": 1, "peer": true}\n'
    assert git(server, "status", "--porcelain") == ""


def test_jede_getrackte_lock_datei_steht_in_der_liste() -> None:
    tracked = subprocess.run(["git", "ls-files", "*package-lock.json"], cwd=REPO_ROOT, check=True,
                             capture_output=True, text=True).stdout.split()
    assert tracked, "keine package-lock.json gefunden"
    owned = subprocess.run(["bash", "-c", f'source "{HELPER}"; printf "%s\\n" "${{HH_GIT_SELF_OWNED[@]}}"'],
                           capture_output=True, text=True).stdout.split()
    assert sorted(owned) == sorted(tracked)


def test_update_laedt_den_git_schritt_von_github() -> None:
    """Befund .4: Der fehlerhafte Git-Schritt lag lokal und hielt jedes Update an, bevor die Reparatur
    ankommen konnte. update.sh lädt ihn deshalb zuerst aus origin/<branch>, lokal nur als Rückfall."""
    text = _code(UPDATE)
    start = text.index('HH_GIT="sudo -u hydrahive git')
    block = text[start:text.index('hh_git_update "$HH_REPO_DIR"', start)]
    assert 'show "origin/$HH_GIT_BRANCH:installer/lib/git-update.sh"' in block
    assert 'bash -n "$HH_GIT_LIB"' in block                       # nur gültiges Skript laden
    assert block.index('source "$HH_GIT_LIB"') < block.index('source "$HH_REPO_DIR/installer/lib/git-update.sh"')
