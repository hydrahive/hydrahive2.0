from __future__ import annotations

import os
from pathlib import Path
import pwd
import subprocess
import sys
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "installer" / "lib" / "python-venv.sh"
UPDATE_SCRIPT = REPO_ROOT / "installer" / "update.sh"
PYTHON_MODULE = REPO_ROOT / "installer" / "modules" / "30-python.sh"
CORE_PYPROJECT = REPO_ROOT / "core" / "pyproject.toml"


def _bash(command: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'set -euo pipefail; source "$1"; {command}', "test-python-venv", str(HELPER)],
        check=True,
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C.UTF-8",
            **(env or {}),
        },
    )


def _needs_rebuild(venv: Path, python: Path) -> bool:
    result = _bash(
        f'if hh_venv_needs_rebuild {str(venv)!r} {str(python)!r}; then echo yes; else echo no; fi'
    )
    return result.stdout.strip() == "yes"


def test_pick_python_requires_absolute_override() -> None:
    result = subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; source "$1"; hh_pick_python',
            "test-python-venv",
            str(HELPER),
        ],
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C.UTF-8",
            "HH_PYTHON": "python3",
        },
    )

    assert result.returncode != 0
    assert "absolut" in result.stderr


def test_pick_python_accepts_explicit_executable() -> None:
    result = _bash("hh_pick_python", env={"HH_PYTHON": sys.executable})

    assert Path(result.stdout.strip()).resolve() == Path(sys.executable).resolve()


def test_dangling_python_symlink_requires_rebuild(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("python3.12")
    (venv / "bin" / "python3").symlink_to("python3.12")

    assert _needs_rebuild(venv, Path(sys.executable))


def test_healthy_matching_venv_is_not_rebuilt(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)

    assert not _needs_rebuild(venv, Path(sys.executable))


def test_ensure_rebuilds_dangling_venv_with_selected_python(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").symlink_to("python3.12")
    (venv / "bin" / "python3").symlink_to("python3.12")
    owner = pwd.getpwuid(os.getuid()).pw_name

    result = _bash(
        f'hh_ensure_python_venv {str(venv)!r} {owner!r} "" {str(tmp_path)!r}; '
        'echo "rebuilt=$HH_VENV_REBUILT"',
        env={"HH_PYTHON": sys.executable},
    )

    assert "rebuilt=1" in result.stdout
    version = subprocess.check_output(
        [str(venv / "bin" / "python"), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        text=True,
    ).strip()
    expected = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert version == expected
    subprocess.run([str(venv / "bin" / "python"), "-m", "pip", "--version"], check=True)


def test_ensure_keeps_healthy_venv_untouched(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    marker = venv / "keep-me"
    marker.write_text("unchanged")
    owner = pwd.getpwuid(os.getuid()).pw_name

    result = _bash(
        f'hh_ensure_python_venv {str(venv)!r} {owner!r} "" {str(tmp_path)!r}; '
        'echo "rebuilt=$HH_VENV_REBUILT"',
        env={"HH_PYTHON": sys.executable},
    )

    assert "rebuilt=0" in result.stdout
    assert marker.read_text() == "unchanged"


def test_update_uses_shared_helper_before_python_module_pip() -> None:
    text = UPDATE_SCRIPT.read_text()

    helper_pos = text.index("python-venv.sh")
    ensure_pos = text.index("hh_ensure_python_venv")
    pip_pos = text.index('"$HH_REPO_DIR/.venv/bin/python" -m pip install')
    assert helper_pos < ensure_pos < pip_pos


def test_fresh_install_module_uses_shared_helper() -> None:
    text = PYTHON_MODULE.read_text()

    assert "python-venv.sh" in text
    assert "hh_ensure_python_venv" in text
    assert "python3.12 -m venv" not in text


def test_core_declares_bounded_voice_bridge_dependency() -> None:
    project = tomllib.loads(CORE_PYPROJECT.read_text())["project"]

    assert "aioesphomeapi>=45.3.1,<46" in project["dependencies"]
