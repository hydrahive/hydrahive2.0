"""Etappe U2 (docs/specs/update-rollback.md §7): Frontend-Bau in dist.neu, Tausch erst nach Erfolg.

Abnahme: Bau scheitert → dist unverändert (Linux update.sh, Mac update-mac.sh, Modul-Installer, Tausch-Bibliothek).
Befund TS2307: ein Bau-Fehler ließ bisher ein halbes dist zurück, das nginx auslieferte.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SWAP = INSTALLER / "lib" / "frontend-swap.sh"
UPDATE = INSTALLER / "update.sh"


def _frontend(tmp_path: Path) -> Path:
    fe = tmp_path / "frontend"
    (fe / "dist").mkdir(parents=True)
    (fe / "dist" / "index.html").write_text("ALT")
    (fe / "dist" / "app.js").write_text("alt-js")
    return fe


def _sh(script: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, **kw)


# --- Tausch-Bibliothek ------------------------------------------------------------------------------------------

def test_swap_ersetzt_dist_und_behaelt_alten_stand(tmp_path):
    fe = _frontend(tmp_path)
    (fe / "dist.neu").mkdir()
    (fe / "dist.neu" / "index.html").write_text("NEU")
    r = _sh(f'source "{SWAP}"; hh_frontend_swap "{fe}"')
    assert r.returncode == 0, r.stderr
    assert (fe / "dist" / "index.html").read_text() == "NEU"
    assert (fe / "dist.alt" / "index.html").read_text() == "ALT"
    assert not (fe / "dist.neu").exists()


def test_swap_ohne_fertigen_bau_laesst_dist_unveraendert(tmp_path):
    fe = _frontend(tmp_path)
    (fe / "dist.neu").mkdir()                         # Halbbau ohne index.html
    r = _sh(f'source "{SWAP}"; hh_frontend_swap "{fe}"')
    assert r.returncode == 1
    assert (fe / "dist" / "index.html").read_text() == "ALT"
    assert (fe / "dist" / "app.js").read_text() == "alt-js"
    assert not (fe / "dist.alt").exists()


def test_swap_ohne_bisheriges_dist(tmp_path):
    fe = tmp_path / "frontend"
    (fe / "dist.neu").mkdir(parents=True)
    (fe / "dist.neu" / "index.html").write_text("NEU")
    assert _sh(f'source "{SWAP}"; hh_frontend_swap "{fe}"').returncode == 0
    assert (fe / "dist" / "index.html").read_text() == "NEU"


def test_swap_ist_rename_im_selben_ordner():
    """Atomar heißt rename, nicht kopieren: kein cp/rsync in der Bibliothek, dist und dist.neu liegen nebeneinander."""
    src = SWAP.read_text()
    assert "cp " not in src and "rsync" not in src
    assert src.count("mv ") >= 3


# --- Linux: der Frontend-Block aus update.sh -----------------------------------------------------------------

def _linux_block() -> str:
    text = UPDATE.read_text()
    a = text.index('source "$HH_REPO_DIR/installer/lib/frontend-swap.sh"')
    b = text.index("WA_BRIDGE_DIR=")
    return text[a:b]


def _run_linux(tmp_path: Path, *, build_ok: bool) -> subprocess.CompletedProcess:
    fe = _frontend(tmp_path)
    repo = tmp_path / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / "installer" / "lib" / "frontend-swap.sh").symlink_to(SWAP)
    (repo / "frontend").symlink_to(fe)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    # sudo -u hydrahive env X=Y npm run build → Attrappe: schreibt einen Halbbau und scheitert bzw. einen vollen Bau
    (bin_ / "sudo").write_text('#!/bin/bash\nshift 2\nexec "$@"\n')
    npm_ok = 'mkdir -p "$HH_FRONTEND_OUTDIR"; echo NEU > "$HH_FRONTEND_OUTDIR/index.html"; exit 0'
    npm_bad = 'mkdir -p "$HH_FRONTEND_OUTDIR"; echo halb > "$HH_FRONTEND_OUTDIR/teil.js"; echo "TS2307" >&2; exit 2'
    (bin_ / "npm").write_text(f"#!/bin/bash\n{npm_ok if build_ok else npm_bad}\n")
    for f in bin_.iterdir():
        f.chmod(0o755)
    script = ('set -euo pipefail\nlog() { echo "LOG $*"; }\n'
              'err() { echo "ERR $*" >&2; exit 1; }\n'
              f'HH_REPO_DIR="{repo}"\ncd "{fe}"\n{_linux_block()}\necho BLOCK-FERTIG\n')
    return _sh(script, env={"PATH": f"{bin_}:/usr/bin:/bin"})


def test_linux_bau_scheitert_dist_unveraendert(tmp_path):
    r = _run_linux(tmp_path, build_ok=False)
    fe = tmp_path / "frontend"
    assert r.returncode != 0 and "ERR Frontend-Bau fehlgeschlagen" in r.stderr, r.stdout + r.stderr
    assert "BLOCK-FERTIG" not in r.stdout
    assert (fe / "dist" / "index.html").read_text() == "ALT"
    assert (fe / "dist" / "app.js").read_text() == "alt-js"
    assert not (fe / "dist.neu").exists(), "Halbbau muss weggeräumt sein"
    assert not (fe / "dist.alt").exists()


def test_linux_bau_ok_tauscht(tmp_path):
    r = _run_linux(tmp_path, build_ok=True)
    fe = tmp_path / "frontend"
    assert r.returncode == 0 and "BLOCK-FERTIG" in r.stdout, r.stdout + r.stderr
    assert (fe / "dist" / "index.html").read_text().strip() == "NEU"
    assert (fe / "dist.alt" / "index.html").read_text() == "ALT"


def test_linux_update_baut_nicht_direkt_nach_dist():
    text = UPDATE.read_text()
    assert "HH_FRONTEND_OUTDIR=dist.neu npm run build" in text
    assert "sudo -u hydrahive npm run build" not in text


# --- Modul-Installer (_frontend_build) -----------------------------------------------------------------------

def _fake_settings(tmp_path: Path):
    class _S:
        base_dir = tmp_path
    return _S


def test_modul_bau_scheitert_dist_unveraendert(tmp_path, monkeypatch):
    from hydrahive.modules import installer
    fe = _frontend(tmp_path)

    def fake_run(cmd, **kw):
        out = fe / kw["env"]["HH_FRONTEND_OUTDIR"]
        out.mkdir(exist_ok=True)
        (out / "teil.js").write_text("halb")
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(installer, "settings", _fake_settings(tmp_path))
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        installer._frontend_build()
    assert (fe / "dist" / "index.html").read_text() == "ALT"
    assert (fe / "dist" / "app.js").read_text() == "alt-js"
    assert not (fe / "dist.neu").exists() and not (fe / "dist.alt").exists()


def test_modul_bau_ok_tauscht(tmp_path, monkeypatch):
    from hydrahive.modules import installer
    fe = _frontend(tmp_path)

    def fake_run(cmd, **kw):
        out = fe / kw["env"]["HH_FRONTEND_OUTDIR"]
        out.mkdir(exist_ok=True)
        (out / "index.html").write_text("NEU")

    monkeypatch.setattr(installer, "settings", _fake_settings(tmp_path))
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    installer._frontend_build()
    assert (fe / "dist" / "index.html").read_text() == "NEU"
    assert (fe / "dist.alt" / "index.html").read_text() == "ALT"
    assert not (fe / "dist.neu").exists()


def test_modul_bau_ohne_index_html_tauscht_nicht(tmp_path, monkeypatch):
    from hydrahive.modules import installer
    fe = _frontend(tmp_path)
    monkeypatch.setattr(installer, "settings", _fake_settings(tmp_path))
    monkeypatch.setattr(installer.subprocess, "run", lambda cmd, **kw: (fe / "dist.neu").mkdir())
    with pytest.raises(installer.InstallError):
        installer._frontend_build()
    assert (fe / "dist" / "index.html").read_text() == "ALT"


def test_modul_bau_raeumt_alten_halbbau_vorher_weg(tmp_path, monkeypatch):
    from hydrahive.modules import installer
    fe = _frontend(tmp_path)
    (fe / "dist.neu").mkdir()
    (fe / "dist.neu" / "rest.js").write_text("rest")

    def fake_run(cmd, **kw):
        assert not (fe / "dist.neu" / "rest.js").exists()
        (fe / "dist.neu").mkdir(exist_ok=True)
        (fe / "dist.neu" / "index.html").write_text("NEU")

    monkeypatch.setattr(installer, "settings", _fake_settings(tmp_path))
    monkeypatch.setattr(installer.subprocess, "run", fake_run)
    installer._frontend_build()
    assert not (fe / "dist" / "rest.js").exists()


# --- vite + Mac-Quelltext -------------------------------------------------------------------------------------

def test_vite_liest_outdir_aus_umgebung():
    cfg = (INSTALLER.parent / "frontend" / "vite.config.ts").read_text()
    assert 'outDir: process.env.HH_FRONTEND_OUTDIR || "dist"' in cfg


def test_nginx_liefert_weiter_dist_aus():
    for f in (INSTALLER / "modules" / "60-nginx.sh", INSTALLER / "modules-mac" / "60-nginx.sh"):
        assert "/frontend/dist;" in f.read_text()
