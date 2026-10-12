"""SearXNG-venv folgt dem System-Python (Spec docs/specs/python-314-umstieg.md).

Prod: SearXNG wurde am 03.06. über die Erweiterung mit `python3 -m venv`
gebaut (damals 3.12), die Migration pin-venv-python.sh hat es auf 3.12
festgenagelt. Ohne Neubau fällt die Websuche aus, sobald 3.12 entfernt wird.

Der Helfer läuft hier ohne Dienstnamen — die Tests dürfen keinen echten
systemd-Dienst anfassen.
"""
from __future__ import annotations

import os
import pwd
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "installer" / "lib"
UPDATE = REPO_ROOT / "installer" / "update.sh"
MODULE = REPO_ROOT / "installer" / "modules" / "76-searxng.sh"
EXTENSION = REPO_ROOT / "extensions" / "install" / "searxng.sh"
OWNER = pwd.getpwuid(os.getuid()).pw_name
MINOR = f"{sys.version_info.major}.{sys.version_info.minor}"


def _sync(searxng_dir: Path) -> subprocess.CompletedProcess[str]:
    script = (
        'set -euo pipefail; source "$1/python-venv.sh"; source "$1/searxng-venv.sh"; '
        'hh_searxng_sync_venv "$2" "$3" ""; echo "rebuilt=$HH_VENV_REBUILT"'
    )
    return subprocess.run(
        ["bash", "-c", script, "sync", str(LIB), str(searxng_dir), OWNER],
        capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
             "LANG": "C.UTF-8", "HH_PYTHON": sys.executable},
    )


def _venv_minor(venv: Path) -> str:
    return subprocess.check_output(
        [str(venv / "bin" / "python"), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], text=True,
    ).strip()


def test_dangling_312_venv_is_rebuilt_with_requirements(tmp_path: Path) -> None:
    """Fall Prod nach dem Entfernen von 3.12: bin/python zeigt ins Leere."""
    searxng = tmp_path / "searxng"
    (searxng / "venv" / "bin").mkdir(parents=True)
    (searxng / "venv" / "bin" / "python").symlink_to("/usr/bin/python3.12-entfernt")
    (searxng / "requirements.txt").write_text("")

    result = _sync(searxng)

    assert result.returncode == 0, result.stderr
    assert "rebuilt=1" in result.stdout
    assert _venv_minor(searxng / "venv") == MINOR
    assert (searxng / "venv" / "bin" / "python").resolve() == Path(sys.executable).resolve()


def test_matching_venv_is_left_alone(tmp_path: Path) -> None:
    searxng = tmp_path / "searxng"
    searxng.mkdir()
    subprocess.run([sys.executable, "-m", "venv", str(searxng / "venv")], check=True)
    marker = searxng / "venv" / "keep-me"
    marker.write_text("x")

    result = _sync(searxng)

    assert "rebuilt=0" in result.stdout
    assert marker.exists()


def test_update_syncs_searxng_venv_before_engine_migration() -> None:
    text = UPDATE.read_text()
    sync = text.index("hh_searxng_sync_venv")

    assert 'source "$HH_REPO_DIR/installer/lib/searxng-venv.sh"' in text
    assert text.index("installer/migrations/pin-venv-python.sh") < sync
    assert sync < text.index("installer/migrations/searxng-engines.sh")
    # Nur wenn SearXNG installiert ist, und ein Fehler bricht das Update nicht ab.
    block = text[text.rindex("\nif ", 0, sync):text.index("\nfi\n", sync)]
    assert "/etc/systemd/system/searxng.service" in block
    assert "|| log" in block
    assert "systemctl restart searxng.service" in block


def test_fresh_installers_use_helper_not_fixed_or_floating_python() -> None:
    for script in (MODULE, EXTENSION):
        text = script.read_text()
        assert "hh_searxng_sync_venv" in text, script.name
        assert "/usr/bin/python3.12" not in text, script.name
        assert "python3 -m venv" not in text, script.name
