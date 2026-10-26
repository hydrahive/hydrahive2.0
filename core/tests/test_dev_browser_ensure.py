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
    env_root = tmp_path / "npm-root"
    calls = tmp_path / "calls.log"
    # npm install -g dev-browser@X legt ein dev-browser-Programm in bin/ an (wie global npm).
    _stub(bin_dir, "npm", f"""
# npm root -g braucht kein Netz – NPM_FAIL betrifft nur Installationen.
[ "$*" = "root -g" ] && {{ echo "{env_root}"; exit 0; }}
[ -n "${{NPM_FAIL:-}}" ] && {{ echo "npm ERR! network" >&2; exit 1; }}
case "$*" in
  *install*-g*dev-browser@*)
    mkdir -p "{env_root}/dev-browser" && printf '{{\n  "name": "dev-browser",\n  "version": "0.2.9"\n}}\n' > "{env_root}/dev-browser/package.json"
    cat > "{bin_dir}/dev-browser" <<'EOF'
#!/bin/bash
echo "dev-browser $*" >> "$CALLS"
if [ "$1" = install ]; then
  [ -n "${{DB_INSTALL_FAIL:-}}" ] && {{ echo "chromium download failed" >&2; exit 1; }}
  [ -n "${{DB_INSTALL_NOOP:-}}" ] && exit 0
  mkdir -p "$HOME/.dev-browser/node_modules" "$HOME/.cache/ms-playwright"
fi
[ "$1" = --version ] && {{ echo "error: unexpected argument '--version' found" >&2; exit 2; }}
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


def _sys_bin(env) -> Path:
    """Nur die Grundbefehle, die das Skript braucht – ohne ein echtes dev-browser/npm des Rechners
    (auf dem Hauptserver liegt seit #627 ein echtes /usr/bin/dev-browser, das die Attrappe verdeckte)."""
    d = env["tmp"] / "sysbin"
    if not d.exists():
        d.mkdir()
        import shutil
        for tool in ("bash", "mkdir", "mktemp", "rm", "tail", "sed", "head", "cat", "chmod", "env", "printf", "dirname"):
            found = shutil.which(tool, path="/usr/bin:/bin")
            if found:
                (d / tool).symlink_to(found)
    return d


def run(env, **extra) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail; log(){{ echo "LOG $*"; }}; source "{HELPER}"; ensure_dev_browser; echo "RC=$?"'
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True,
        env={"PATH": f"{env['bin']}:{_sys_bin(env)}", "CALLS": str(env["calls"]), "HH_USER": "hydrahive",
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
    assert "Browser-Werkzeug bereit (dev-browser 0.2.9)" in r.stdout


def test_alles_da_nichts_passiert(env) -> None:
    run(env)
    env["calls"].unlink()
    r = run(env)
    assert r.returncode == 0
    assert "npm install" not in calls(env) and "dev-browser install" not in calls(env)
    assert "Browser-Werkzeug vorhanden (dev-browser 0.2.9)" in r.stdout


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


# --- Ältere Version wird angehoben (Task f24c39bf, Befund .4: 0.2.7 statt 0.2.9) ----------------------------------

def _set_installed(env, version: str) -> None:
    """Zustand wie auf der .4: dev-browser in alter Version mit eingerichteter Laufzeit."""
    run(env)
    pkg = env["tmp"] / "npm-root" / "dev-browser" / "package.json"
    pkg.write_text(f'{{\n  "name": "dev-browser",\n  "version": "{version}"\n}}\n')
    env["calls"].unlink()


def test_alte_version_wird_angehoben(env) -> None:
    _set_installed(env, "0.2.7")
    r = run(env)
    assert r.returncode == 0, r.stderr
    c = calls(env)
    assert re.search(r"^npm install -g .*dev-browser@0\.2\.9$", c, re.M)
    assert "Browser-Werkzeug: dev-browser 0.2.7 → 0.2.9 anheben" in r.stdout
    # Neue Version → Laufzeit/Chromium passend neu einrichten, auch wenn die alten Ordner noch da sind.
    assert "dev-browser install" in c
    assert "Browser-Werkzeug bereit (dev-browser 0.2.9)" in r.stdout


def test_neuere_version_wird_auf_soll_gesetzt(env) -> None:
    """Soll ist bewusst fest (kein ungeprüfter 1.0-Sprung) – auch eine abweichend neuere wird zurückgesetzt."""
    _set_installed(env, "1.0.0-rc.4")
    r = run(env)
    assert re.search(r"^npm install -g .*dev-browser@0\.2\.9$", calls(env), re.M)
    assert "1.0.0-rc.4 → 0.2.9" in r.stdout


def test_soll_version_kein_npm(env) -> None:
    _set_installed(env, "0.2.9")
    run(env)
    assert "npm install" not in calls(env) and "dev-browser install" not in calls(env)


def test_anheben_scheitert_warnung_alte_bleibt(env) -> None:
    _set_installed(env, "0.2.7")
    r = run(env, NPM_FAIL="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG: dev-browser-Anhebung fehlgeschlagen – 0.2.7 bleibt" in r.stdout
    assert "dev-browser install" not in calls(env)


def test_version_unbekannt_wird_nicht_angehoben(env) -> None:
    """Ohne lesbare package.json (z. B. anders installiert) nichts erzwingen – nur melden."""
    _set_installed(env, "0.2.9")
    (env["tmp"] / "npm-root" / "dev-browser" / "package.json").unlink()
    r = run(env)
    assert "npm install" not in calls(env)
    assert r.returncode == 0
