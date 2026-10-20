"""macOS-Update (Spec docs/specs/mac-update.md): Verlauf im Update-Fenster, Python-Pakete heil, Frontend-Build.

Befund 20.10.2026: Mac-Nutzer sah im Update-Fenster keinen Verlauf (Backend liest $HH_LOG_DIR, Standard /var/log;
der Mac schreibt nach /usr/local/var/log). Zuvor scheiterte jeder Modellaufruf an gemischten LiteLLM-Dateien.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
LAUNCHD = INSTALLER / "modules-mac" / "50-launchd.sh"
TRIGGERS = INSTALLER / "modules-mac" / "55-launchd-triggers.sh"
UPDATE = INSTALLER / "update-mac.sh"
WRAPPER = INSTALLER / "lib" / "mac-backend-start.sh"
MAC_LOG_DIR = "/usr/local/var/log"


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    """Testumgebung: sudo/launchctl/brew/git/npm als Attrappen, pip im venv als Attrappe mit Steuerdateien."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.log"
    calls.write_text("")
    (bin_ / "sudo").write_text('#!/bin/bash\n[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    (bin_ / "launchctl").write_text(f'#!/bin/bash\necho "launchctl $*" >> "{calls}"\n'
                                    'case "$1" in list) echo "123 0 io.hydrahive.backend";; esac\n')
    (bin_ / "brew").write_text("#!/bin/bash\necho /usr/local\n")
    # git: rev-parse liefert alt/neu je nach Aufruf, diff liefert den Inhalt von git_diff.txt
    (bin_ / "git").write_text(f'''#!/bin/bash
echo "git $*" >> "{calls}"
case "$*" in
  *"rev-parse HEAD"*) if [ -f "{tmp_path}/pulled" ]; then echo neu111; else echo alt000; fi;;
  *pull*) touch "{tmp_path}/pulled"; echo "Already up to date.";;
  *diff*) cat "{tmp_path}/git_diff.txt" 2>/dev/null;;
esac
exit 0
''')
    (bin_ / "npm").write_text(f'#!/bin/bash\necho "npm $*" >> "{calls}"\necho "npm-ausgabe $1"\n')
    for f in bin_.iterdir():
        f.chmod(0o755)
    cfg = tmp_path / "etc"
    cfg.mkdir()
    (cfg / "secret_key").write_text("x" * 48 + "\n")
    (cfg / "secret_key").chmod(0o600)
    repo = tmp_path / "repo"
    (repo / "installer" / "lib").mkdir(parents=True)
    (repo / "installer" / "modules-mac").symlink_to(INSTALLER / "modules-mac")
    (repo / "installer" / "lib" / "mac-backend-start.sh").symlink_to(WRAPPER)
    (repo / "frontend" / "dist").mkdir(parents=True)
    (repo / "frontend" / "dist" / "index.html").write_text("<html/>")
    venv = repo / ".venv" / "bin"
    venv.mkdir(parents=True)
    # pip-Attrappe: Aufrufe protokollieren; `check` meldet den Inhalt von pip_check.txt (dann Exit 1)
    (venv / "pip").write_text(f'''#!/bin/bash
echo "pip $*" >> "{calls}"
if [ "$1" = "check" ]; then
  if [ -s "{tmp_path}/pip_check.txt" ]; then cat "{tmp_path}/pip_check.txt"; exit 1; fi
  echo "No broken requirements found."; exit 0
fi
echo "pip-ausgabe $1"
''')
    # python-Attrappe: `-c import litellm` scheitert, wenn litellm_kaputt existiert
    (venv / "python").write_text(f'''#!/bin/bash
echo "python $*" >> "{calls}"
if [ "$1" = "-c" ] && [[ "$2" == *"import litellm"* ]] && [ -f "{tmp_path}/litellm_kaputt" ]; then
  echo "AttributeError: should_use_litellm_mcp_gateway" >&2; exit 1
fi
exit 0
''')
    for f in venv.iterdir():
        f.chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    return {"tmp": tmp_path, "bin": bin_, "cfg": cfg, "repo": repo, "calls": calls, "data": data,
            "plist": tmp_path / "io.hydrahive.backend.plist", "log": tmp_path / "update.log"}


def _env(m: dict) -> dict:
    return {**os.environ, "PATH": f"{m['bin']}:{os.environ['PATH']}",
            "HH_CONFIG_DIR": str(m["cfg"]), "HH_DATA_DIR": str(m["data"]), "HH_REPO_DIR": str(m["repo"]),
            "HH_USER": "tester", "HH_HOST": "127.0.0.1", "HH_PORT": "8001",
            "HH_BACKEND_PLIST": str(m["plist"]), "HH_UPDATE_LOG": str(m["log"])}


def _launchd(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(LAUNCHD)], env=_env(m), capture_output=True, text=True, timeout=60)


def _update(m: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(UPDATE)], env=_env(m), capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> str:
    return m["calls"].read_text()


# --- 1. Verlauf im Update-Fenster ------------------------------------------------------------------

def test_plist_sets_log_dir_to_mac_log_folder(mac):
    r = _launchd(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    env = plistlib.loads(mac["plist"].read_bytes())["EnvironmentVariables"]
    assert env["HH_LOG_DIR"] == MAC_LOG_DIR


def test_backend_reads_the_file_the_mac_update_writes():
    """Was das Backend mit diesem HH_LOG_DIR liest, ist genau die Datei des Mac-Updates."""
    text = UPDATE.read_text() + TRIGGERS.read_text()
    assert f"{MAC_LOG_DIR}/hydrahive2-update.log" in text
    code = ("import os; os.environ['HH_LOG_DIR']=%r; from hydrahive.settings import settings; print(settings.update_log)"
            % MAC_LOG_DIR)
    out = subprocess.run(["python", "-c", code], capture_output=True, text=True, timeout=60,
                         env={**os.environ, "PYTHONPATH": str(INSTALLER.parent / "core" / "src")})
    assert out.stdout.strip() == f"{MAC_LOG_DIR}/hydrahive2-update.log", out.stderr


def test_update_rewrites_plist_without_log_dir(mac):
    _launchd(mac)
    raw = mac["plist"].read_text()
    start = raw.index("<key>HH_LOG_DIR</key>")
    old = raw[:start] + raw[raw.index("</string>", start) + len("</string>"):]
    mac["plist"].write_text(old)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "HH_LOG_DIR" in mac["plist"].read_text()


def test_update_leaves_current_plist_alone(mac):
    _launchd(mac)
    before = mac["plist"].read_bytes()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert mac["plist"].read_bytes() == before


# --- 2. Python-Pakete heil -------------------------------------------------------------------------

def test_healthy_packages_are_not_reinstalled(mac):
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "pip install" in calls and "-e " in calls and "pip check" in calls
    assert "--force-reinstall" not in calls


def test_broken_package_from_pip_check_is_reinstalled(mac):
    _launchd(mac)
    (mac["tmp"] / "pip_check.txt").write_text("litellm 1.106.0 has requirement openai>=2, but you have openai 1.0.\n"
                                             "fastapi 0.120.0 has requirement starlette<0.50, but you have starlette 0.9.\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "pip install --force-reinstall --no-deps litellm" in calls
    assert "pip install --force-reinstall --no-deps fastapi" in calls
    assert calls.count("--force-reinstall") == 2


def test_broken_litellm_import_is_reinstalled(mac):
    """Gemischte Dateien merkt pip check nicht – der Import zeigt es."""
    _launchd(mac)
    (mac["tmp"] / "litellm_kaputt").touch()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pip install --force-reinstall --no-deps litellm" in _calls(mac)
    assert "LiteLLM" in mac["log"].read_text()


def test_package_names_from_pip_check_are_safe(mac):
    """Nur echte Paketnamen werden übernommen, nichts aus dem Text wird als Befehl ausgeführt."""
    _launchd(mac)
    (mac["tmp"] / "pip_check.txt").write_text("$(touch /tmp/boese) 1.0 has requirement x\n;rm -rf / 2 has requirement y\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--force-reinstall" not in _calls(mac)


# --- 3. Frontend ------------------------------------------------------------------------------------

def test_frontend_change_triggers_build(mac):
    _launchd(mac)
    (mac["tmp"] / "git_diff.txt").write_text("frontend/src/App.tsx\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert "git diff --name-only alt000 neu111 -- frontend/" in calls
    assert "npm install" in calls and "npm run build" in calls


def test_no_frontend_change_no_build(mac):
    _launchd(mac)
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" not in _calls(mac)


def test_missing_dist_triggers_build(mac):
    _launchd(mac)
    (mac["repo"] / "frontend" / "dist" / "index.html").unlink()
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "npm run build" in _calls(mac)


def test_git_runs_as_service_user(mac):
    """Alle git-Aufrufe über sudo -u (sonst „dubious ownership“ als root)."""
    (mac["bin"] / "sudo").write_text(f'#!/bin/bash\necho "sudo $*" >> "{mac["calls"]}"\n'
                                     '[ "$1" = "-u" ] && shift 2\nexec "$@"\n')
    _launchd(mac)
    mac["calls"].write_text("")
    (mac["tmp"] / "git_diff.txt").write_text("frontend/x.ts\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac).splitlines()
    git_lines = [c for c in calls if c.startswith("git ")]
    sudo_git = [c for c in calls if c.startswith("sudo -u tester git ")]
    assert git_lines and len(sudo_git) == len(git_lines)


# --- 4. Alles im Verlauf ----------------------------------------------------------------------------

def test_pip_and_npm_output_land_in_the_log(mac):
    _launchd(mac)
    (mac["tmp"] / "git_diff.txt").write_text("frontend/x.ts\n")
    r = _update(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    log = mac["log"].read_text()
    assert "pip-ausgabe install" in log
    assert "npm-ausgabe install" in log and "npm-ausgabe run" in log
    assert "Update abgeschlossen" in log
