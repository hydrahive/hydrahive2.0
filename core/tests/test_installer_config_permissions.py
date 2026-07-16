from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import subprocess


HELPER = Path(__file__).parents[2] / "installer" / "lib" / "config-permissions.sh"


def _run_helper(config_dir: Path) -> None:
    user = pwd.getpwuid(os.getuid()).pw_name
    subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; log() { :; }; source "$1"; repair_llm_config_permissions',
            "test-config-permissions",
            str(HELPER),
        ],
        env={**os.environ, "HH_CONFIG_DIR": str(config_dir), "HH_USER": user},
        check=True,
    )


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_repair_llm_config_permissions(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(mode=0o700)
    llm_config = config_dir / "llm.json"
    llm_config.write_text('{"providers": []}')
    llm_config.chmod(0o444)

    _run_helper(config_dir)

    assert _mode(config_dir) == 0o750
    assert _mode(llm_config) == 0o640
    assert llm_config.stat().st_uid == os.getuid()


def test_repair_rejects_llm_config_symlink(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(mode=0o700)
    target = tmp_path / "outside.json"
    target.write_text("secret")
    target.chmod(0o600)
    (config_dir / "llm.json").symlink_to(target)

    _run_helper(config_dir)

    assert _mode(target) == 0o600
