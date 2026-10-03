from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import subprocess


HELPER = Path(__file__).parents[2] / "installer" / "lib" / "ssh-include.sh"


def _run_helper(home: Path, data_dir: Path) -> None:
    user = pwd.getpwuid(os.getuid()).pw_name
    subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; log() { :; }; source "$1"; ensure_ssh_credentials_include',
            "test-ssh-include",
            str(HELPER),
        ],
        env={**os.environ, "HH_SSH_HOME": str(home), "HH_DATA_DIR": str(data_dir), "HH_USER": user},
        check=True,
    )


def _include(data_dir: Path) -> str:
    return f"Include {data_dir}/.ssh/config"


def test_creates_config_with_include(tmp_path: Path) -> None:
    home, data = tmp_path / "home", tmp_path / "data"
    home.mkdir()

    _run_helper(home, data)

    cfg = home / ".ssh" / "config"
    assert _include(data) in cfg.read_text().splitlines()
    assert stat.S_IMODE(cfg.stat().st_mode) == 0o600
    assert stat.S_IMODE((home / ".ssh").stat().st_mode) == 0o700


def test_prepends_include_and_keeps_existing_hosts(tmp_path: Path) -> None:
    home, data = tmp_path / "home", tmp_path / "data"
    (home / ".ssh").mkdir(parents=True)
    cfg = home / ".ssh" / "config"
    cfg.write_text("Host example\n    User bob\n")

    _run_helper(home, data)

    lines = cfg.read_text().splitlines()
    assert lines.index(_include(data)) < lines.index("Host example")
    assert "    User bob" in lines


def test_is_idempotent(tmp_path: Path) -> None:
    home, data = tmp_path / "home", tmp_path / "data"
    home.mkdir()

    _run_helper(home, data)
    first = (home / ".ssh" / "config").read_text()
    _run_helper(home, data)

    assert (home / ".ssh" / "config").read_text() == first
    assert first.count(_include(data)) == 1


def test_skips_symlinked_config(tmp_path: Path) -> None:
    home, data = tmp_path / "home", tmp_path / "data"
    (home / ".ssh").mkdir(parents=True)
    target = tmp_path / "outside"
    target.write_text("untouched\n")
    (home / ".ssh" / "config").symlink_to(target)

    _run_helper(home, data)

    assert target.read_text() == "untouched\n"
