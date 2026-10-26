"""mmx-cli auf die feste Soll-Version anheben (docs/specs/system-updates.md, Task f24c39bf).

Befund 26.10.2026: .2 hatte mmx-cli 1.0.28, hydratest 1.0.12 – installiert wurde nur, wenn es fehlte,
ohne feste Version. Attrappen für npm, kein Netz, kein root.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "installer" / "lib" / "mmx-cli.sh"
UPDATE = REPO / "installer" / "update.sh"
DEPS = REPO / "installer" / "modules" / "00-deps.sh"
VOICE = REPO / "installer" / "modules" / "55-voice.sh"


@pytest.fixture
def env(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sysbin = tmp_path / "sysbin"
    sysbin.mkdir()
    for tool in ("bash", "sed", "head", "cat", "printf", "mkdir", "tail"):
        found = shutil.which(tool, path="/usr/bin:/bin")
        if found:
            (sysbin / tool).symlink_to(found)
    root = tmp_path / "npm-root"
    calls = tmp_path / "calls.log"
    (bin_dir / "npm").write_text(f"""#!/bin/bash
echo "npm $*" >> "$CALLS"
[ "$*" = "root -g" ] && {{ echo "{root}"; exit 0; }}
[ -n "${{NPM_FAIL:-}}" ] && {{ echo "npm ERR! 503" >&2; exit 1; }}
case "$*" in *install*-g*mmx-cli@*)
  for a in "$@"; do case "$a" in mmx-cli@*) v="${{a#mmx-cli@}}" ;; esac; done
  mkdir -p "{root}/mmx-cli"; printf '{{"name":"mmx-cli","version":"%s"}}\\n' "$v" > "{root}/mmx-cli/package.json" ;;
esac
exit 0
""")
    (bin_dir / "npm").chmod(0o755)
    return {"bin": bin_dir, "sysbin": sysbin, "root": root, "calls": calls}


def _installed(env, version: str) -> None:
    (env["root"] / "mmx-cli").mkdir(parents=True)
    (env["root"] / "mmx-cli" / "package.json").write_text(f'{{"name":"mmx-cli","version":"{version}"}}\n')
    mmx = env["bin"] / "mmx"
    mmx.write_text("#!/bin/bash\nexit 0\n")
    mmx.chmod(0o755)


def run(env, **extra) -> subprocess.CompletedProcess[str]:
    script = f'set -euo pipefail; log(){{ echo "LOG $*"; }}; source "{LIB}"; ensure_mmx_cli; echo "RC=$?"'
    e = {"PATH": f"{env['bin']}:{env['sysbin']}", "CALLS": str(env["calls"])}
    e.update(extra)
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=e)


def _calls(env) -> str:
    return env["calls"].read_text() if env["calls"].exists() else ""


def test_alte_version_wird_angehoben(env) -> None:
    _installed(env, "1.0.12")
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert re.search(r"^npm install -g .*mmx-cli@1\.0\.28$", _calls(env), re.M)
    assert "mmx-cli 1.0.12 → 1.0.28 anheben" in r.stdout
    assert "mmx-cli 1.0.28 bereit" in r.stdout


def test_soll_version_nichts(env) -> None:
    _installed(env, "1.0.28")
    r = run(env)
    assert "install" not in _calls(env)
    assert "mmx-cli aktuell (1.0.28)" in r.stdout


def test_nicht_installiert_nichts(env) -> None:
    """Neu installiert wird mmx von 00-deps.sh/55-voice.sh – das Update hebt nur an."""
    r = run(env)
    assert "RC=0" in r.stdout
    assert "install" not in _calls(env)


def test_fehler_nur_warnung(env) -> None:
    _installed(env, "1.0.12")
    r = run(env, NPM_FAIL="1")
    assert "RC=0" in r.stdout
    assert "WARNUNG: mmx-cli-Anhebung fehlgeschlagen – 1.0.12 bleibt" in r.stdout


def test_soll_version_ueberschreibbar(env) -> None:
    _installed(env, "1.0.28")
    run(env, HH_MMX_VERSION="1.0.30")
    assert re.search(r"mmx-cli@1\.0\.30$", _calls(env), re.M)


def _code(path: Path) -> str:
    return "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("#"))


def test_update_ruft_ensure_auf() -> None:
    text = _code(UPDATE)
    assert re.search(r'source "\$HH_REPO_DIR/installer/lib/mmx-cli\.sh"', text)
    assert re.search(r"^\s*ensure_mmx_cli\s*$", text, re.M)


def test_neuinstallation_nutzt_soll_version() -> None:
    for path in (DEPS, VOICE):
        text = _code(path)
        assert "npm install -g mmx-cli " not in text and "npm install -g mmx-cli\n" not in text, path.name
        assert 'mmx-cli@$HH_MMX_VERSION' in text or 'mmx-cli@${HH_MMX_VERSION}' in text, path.name
        assert "lib/mmx-cli.sh" in text, path.name
