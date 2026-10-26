"""dev-browser bei Installation und Update sicherstellen (Task 3d517e82,
docs/specs/dev-browser-nachinstallieren.md).

Befund: installer/modules/87-mcp-servers.sh richtete dev-browser ein, wurde aber
seit Mai nie von install.sh oder update.sh aufgerufen – auf dem Hauptserver fehlte
das Browser-Werkzeug nach dem Umzug, draußen bei neuen Installationen immer.

Getestet gegen PATH-Attrappen für npm, dev-browser und sudo: jede protokolliert
ihre Aufrufe und simuliert Erfolg oder Fehlschlag. Kein Netz, kein root.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / "installer" / "lib" / "dev-browser.sh"
INSTALL = REPO / "installer" / "install.sh"
UPDATE = REPO / "installer" / "update.sh"
MCP = REPO / "installer" / "modules" / "87-mcp-servers.sh"
TOOL = REPO / "core" / "src" / "hydrahive" / "tools" / "web_browser.py"


def _stub(bin_dir: Path, name: str, body: str) -> None:
    p = bin_dir / name
    p.write_text(f"#!/bin/bash\necho \"{name} $*\" >> \"$CALLS\"\n{body}\n")
    p.chmod(0o755)


@pytest.fixture
def env(tmp_path: Path):
    """bin/ mit npm und sudo; dev-browser entsteht erst, wenn npm es „installiert“."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "hh-dev-browser-home"
    calls = tmp_path / "calls.log"
    # npm install -g dev-browser@X legt ein dev-browser-Programm in bin/ an (wie global npm).
    _stub(bin_dir, "npm", f"""
[ -n "${{NPM_FAIL:-}}" ] && {{ echo "npm ERR! network" >&2; exit 1; }}
case "$*" in
  *install*-g*dev-browser@*)
    cat > "{bin_dir}/dev-browser" <<'EOF'
#!/bin/bash
echo "dev-browser $*" >> "$CALLS"
if [ "$1" = install ]; then
  [ -n "${{DB_INSTALL_FAIL:-}}" ] && {{ echo "chromium download failed" >&2; exit 1; }}
  [ -n "${{DB_INSTALL_NOOP:-}}" ] && exit 0
  mkdir -p "$HOME/.dev-browser/node_modules" "$HOME/.cache/ms-playwright"
fi
[ "$1" = --version ] && echo "0.2.9"
exit 0
EOF
    chmod +x "{bin_dir}/dev-browser" ;;
esac
exit 0
""")
    # sudo -u USER env HOME=… cmd … → Befehl ohne Benutzerwechsel ausführen.
    # sudo -u USER env HOME=… cmd … → Befehl ohne Benutzerwechsel; PATH bleibt (Attrappen finden).
    _stub(bin_dir, "sudo", """
while :; do case "$1" in -u) shift 2 ;; -H) shift ;; *) break ;; esac; done
if [ "$1" = env ]; then shift; exec env "PATH=$PATH" "$@"; fi
exec "$@"
""")
    _stub(bin_dir, "chown", "exit 0")
    return {"bin": bin_dir, "home": home, "calls": calls, "tmp": tmp_path}


def run(env, **extra) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail; log(){{ echo "LOG $*"; }}; source "{HELPER}"; ensure_dev_browser; echo "RC=$?"'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True,
        env={"PATH": f"{env['bin']}:/usr/bin:/bin", "CALLS": str(env["calls"]), "HH_USER": "hydrahive",
             "DEV_BROWSER_HOME": str(env["home"]), "TMPDIR": str(env["tmp"]), **extra},
    )


def calls(env) -> str:
    return env["calls"].read_text() if env["calls"].exists() else ""


def test_fehlt_komplett_wird_installiert(env) -> None:
    r = run(env)
    assert r.returncode == 0, r.stderr
    c = calls(env)
    assert re.search(r"^npm install -g .*dev-browser@0\.2\.9$", c, re.M)
    assert "dev-browser install" in c
    assert (env["home"] / ".dev-browser" / "node_modules").is_dir()
    assert (env["home"] / ".cache" / "ms-playwright").is_dir()
    assert "Browser-Werkzeug bereit" in r.stdout


def test_alles_da_nichts_passiert(env) -> None:
    run(env)
    env["calls"].unlink()
    r = run(env)
    assert r.returncode == 0
    assert "npm" not in calls(env) and "dev-browser install" not in calls(env)
    assert "vorhanden" in r.stdout


def test_nur_chromium_fehlt_nur_install(env) -> None:
    run(env)
    import shutil
    shutil.rmtree(env["home"] / ".cache")
    env["calls"].unlink()
    r = run(env)
    assert r.returncode == 0
    c = calls(env)
    assert "npm install" not in c
    assert "dev-browser install" in c
    assert (env["home"] / ".cache" / "ms-playwright").is_dir()


def test_nur_laufzeit_fehlt_nur_install(env) -> None:
    run(env)
    import shutil
    shutil.rmtree(env["home"] / ".dev-browser")
    env["calls"].unlink()
    r = run(env)
    assert r.returncode == 0
    assert "npm install" not in calls(env) and "dev-browser install" in calls(env)


def test_npm_scheitert_warnung_kein_abbruch(env) -> None:
    r = run(env, NPM_FAIL="1")
    assert "RC=0" in r.stdout                      # Installation läuft weiter
    assert "WARNUNG" in r.stdout and "npm ERR! network" in r.stdout
    assert "dev-browser install" not in calls(env)


def test_install_scheitert_warnung_mit_grund(env) -> None:
    r = run(env, DB_INSTALL_FAIL="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG" in r.stdout and "chromium download failed" in r.stdout
    assert "Browser-Werkzeug bereit" not in r.stdout


def test_install_meldet_erfolg_legt_aber_nichts_an(env) -> None:
    """Wie auf hydratest am 02.10.: „installiert“ gemeldet, aber nichts da."""
    r = run(env, DB_INSTALL_NOOP="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG" in r.stdout
    assert "Browser-Werkzeug bereit" not in r.stdout


def test_install_laeuft_mit_eigenem_home(env) -> None:
    run(env)
    line = next(l for l in calls(env).splitlines() if l.startswith("sudo "))
    assert "-u hydrahive" in line and f"HOME={env['home']}" in line and "dev-browser install" in line


def _code(path: Path) -> str:
    return "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("#"))


def test_install_update_und_modul_nutzen_ensure() -> None:
    for path in (INSTALL, UPDATE, MCP):
        text = _code(path)
        assert re.search(r'source "\$[A-Z_]+/(installer/)?lib/dev-browser\.sh"', text), path.name
        assert re.search(r"^\s*ensure_dev_browser\s*$", text, re.M), path.name
    assert "npm install -g --silent dev-browser" not in _code(MCP)


def test_werkzeug_fehler_verstaendlich() -> None:
    text = TOOL.read_text()
    assert "npm install -g dev-browser" not in text
    assert "System aktualisieren" in text
