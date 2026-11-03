from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAC_HELPER = ROOT / "installer/lib/mac-document-tools.sh"
MAC_DEPS = ROOT / "installer/modules-mac/00-deps.sh"
MAC_UPDATE = ROOT / "installer/update-mac.sh"
DEBIAN_HELPER = ROOT / "installer/lib/debian-document-tools.sh"
DEBIAN_DEPS = ROOT / "installer/modules/00-deps.sh"
DEBIAN_UPDATE = ROOT / "installer/update.sh"
APPARMOR_PROFILE = ROOT / "installer/lib/hydrahive-bwrap-userns.apparmor"


def _executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _document_commands(bin_dir: Path, languages: str = "deu") -> None:
    for name in ("pdfinfo", "pdftotext", "pdftoppm"):
        _executable(bin_dir / name, "#!/bin/bash\nexit 0\n")
    _executable(bin_dir / "tesseract", f'#!/bin/bash\n[ "$1" = --list-langs ] && echo "{languages}"\n')


def _mac_env(bin_dir: Path, brew: Path, **extra: str) -> dict[str, str]:
    user = os.environ.get("USER", "root")
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HH_BREW": str(brew), "HH_BREW_USER": user, "HH_USER": user,
        **extra,
    }


def test_mac_installer_and_update_use_role_aware_document_helper() -> None:
    helper = MAC_HELPER.read_text(encoding="utf-8")
    deps = MAC_DEPS.read_text(encoding="utf-8")
    update = MAC_UPDATE.read_text(encoding="utf-8")

    assert "mac-roles.sh" in helper
    assert "as_brew" in helper
    assert "HH_DOC_" not in helper
    assert '$(/usr/bin/id -u)" -ne 0' in helper
    assert {"poppler", "tesseract", "tesseract-lang"} <= set(helper.replace('"', "").split())
    assert "mac-document-tools.sh" in deps
    assert "brew shellenv" not in update
    assert "export PATH" not in update
    assert '/usr/bin/sudo -H -u "$HH_BREW_USER"' in update
    assert 'env "PATH=$HH_BREW_PATH" git pull --ff-only' in update
    assert update.index("git pull --ff-only") < update.index("mac-document-tools.sh")


def test_mac_helper_installs_only_missing_formulas(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "brew", f'''#!/bin/bash
if [ "$1" = list ]; then [ "$3" = poppler ] && exit 0; exit 1; fi
if [ "$1" = install ]; then echo "$2" >> "{calls}"; exit 0; fi
exit 0
''')
    _document_commands(bin_dir)

    result = subprocess.run(["bash", str(MAC_HELPER)], env=_mac_env(bin_dir, bin_dir / "brew"),
                            text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["tesseract", "tesseract-lang"]


def test_mac_helper_is_idempotent_when_everything_is_installed(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "brew", f'#!/bin/bash\necho "$*" >> "{calls}"\n[ "$1" = list ]\n')
    _document_commands(bin_dir)

    result = subprocess.run(["bash", str(MAC_HELPER)], env=_mac_env(bin_dir, bin_dir / "brew"),
                            text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert all(not line.startswith("install ") for line in calls.read_text().splitlines())


def test_mac_helper_separates_service_and_brew_owner(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "sudo", f'''#!/bin/bash
echo "sudo $*" >> "{calls}"
[ "$1" = -H ] && shift
[ "$1" = -u ] && shift 2
exec "$@"
''')
    _executable(bin_dir / "brew", f'#!/bin/bash\necho "brew $*" >> "{calls}"\n[ "$1" = list ]\n')
    _document_commands(bin_dir)
    env = _mac_env(bin_dir, bin_dir / "brew", HH_USER="_hydrahive", HH_BREW_USER="macowner")

    result = subprocess.run(["bash", str(MAC_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    lines = calls.read_text().splitlines()
    sudo_lines = [line for line in lines if line.startswith("sudo ")]
    assert len(sudo_lines) == 3
    assert all(line.startswith(f"sudo -u macowner {bin_dir}/brew ") for line in sudo_lines)
    assert not any("_hydrahive" in line for line in lines)


@pytest.mark.parametrize("prefix", ["opt/homebrew", "usr/local"])
def test_mac_helper_finds_apple_silicon_and_intel_brew(tmp_path: Path, prefix: str) -> None:
    brew = tmp_path / prefix / "bin/brew"
    calls = tmp_path / "calls"
    _executable(brew, f'#!/bin/bash\necho "$0 $*" >> "{calls}"\n[ "$1" = list ]\n')
    _document_commands(brew.parent)
    user = os.environ.get("USER", "root")
    env = {**os.environ, "PATH": f"{brew.parent}:{os.environ['PATH']}", "HH_USER": user,
           "HH_BREW_USER": user, "HH_BREW_CANDIDATES": str(brew)}
    env.pop("HH_BREW", None)

    result = subprocess.run(["bash", str(MAC_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert str(brew) in calls.read_text()


def _restricted_mac_env(tmp_path: Path, languages: str) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("dirname", "id", "grep"):
        (bin_dir / name).symlink_to(Path("/usr/bin") / name)
    brew = bin_dir / "brew"
    _executable(brew, "#!/bin/bash\n[ \"$1\" = list ]\n")
    _document_commands(bin_dir, languages)
    user = os.environ.get("USER", "root")
    return {**os.environ, "PATH": str(bin_dir), "HH_BREW": str(brew),
            "HH_BREW_USER": user, "HH_USER": user}, bin_dir


def test_mac_helper_fails_when_binary_is_missing_after_install(tmp_path: Path) -> None:
    env, bin_dir = _restricted_mac_env(tmp_path, "deu")
    (bin_dir / "pdftoppm").unlink()

    result = subprocess.run(["/bin/bash", str(MAC_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode != 0
    assert "pdftoppm" in result.stderr


def test_mac_helper_fails_when_german_language_is_missing(tmp_path: Path) -> None:
    env, _ = _restricted_mac_env(tmp_path, "eng")

    result = subprocess.run(["/bin/bash", str(MAC_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode != 0
    assert "Deutsche" in result.stderr


def _debian_env(bin_dir: Path, tmp_path: Path) -> dict[str, str]:
    _executable(bin_dir / "install", "#!/bin/bash\nexec /usr/bin/install \"$@\"\n")
    _executable(bin_dir / "apparmor_parser", "#!/bin/bash\nexit 0\n")
    _executable(bin_dir / "runuser", "#!/bin/bash\nexit 0\n")
    _executable(bin_dir / "bwrap", "#!/bin/bash\nexit 0\n")
    return {
        **os.environ,
        "HH_DPKG_QUERY": str(bin_dir / "dpkg-query"),
        "HH_APT_GET": str(bin_dir / "apt-get"),
        "HH_INSTALL_BIN": str(bin_dir / "install"),
        "HH_APPARMOR_PARSER": str(bin_dir / "apparmor_parser"),
        "HH_RUNUSER": str(bin_dir / "runuser"),
        "HH_BWRAP": str(bin_dir / "bwrap"),
        "HH_APPARMOR_PROFILE_TARGET": str(tmp_path / "apparmor-profile"),
    }


def test_debian_first_install_and_update_include_document_packages() -> None:
    deps = DEBIAN_DEPS.read_text(encoding="utf-8")
    update = DEBIAN_UPDATE.read_text(encoding="utf-8")
    packages = {"poppler-utils", "tesseract-ocr", "tesseract-ocr-deu", "tesseract-ocr-eng", "bubblewrap", "apparmor", "util-linux"}

    profile = APPARMOR_PROFILE.read_text(encoding="utf-8")
    assert all(package in deps for package in packages)
    assert "debian-document-tools.sh" in deps
    assert "profile bwrap /usr/bin/bwrap" in profile
    assert "allow userns," in profile and "allow mount," in profile
    assert "profile unpriv_bwrap" in profile
    assert "audit deny capability," in profile
    assert "debian-document-tools.sh" in update
    assert update.index("git pull") < update.index("debian-document-tools.sh")
    assert 'bash "$HH_REPO_DIR/installer/lib/debian-document-tools.sh" ||' not in update


def test_debian_helper_installs_only_missing_packages(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "dpkg-query", "#!/bin/bash\ncase \"$*\" in *poppler-utils*) echo 'install ok installed';; *) exit 1;; esac\n")
    _executable(bin_dir / "apt-get", f'#!/bin/bash\necho "$*" >> "{calls}"\n')

    env = _debian_env(bin_dir, tmp_path)
    result = subprocess.run(["bash", str(DEBIAN_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    lines = calls.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "update"
    assert lines[1].startswith("install -y ")
    assert "poppler-utils" not in lines[1]
    assert all(package in lines[1] for package in (
        "tesseract-ocr", "tesseract-ocr-deu", "tesseract-ocr-eng", "bubblewrap", "apparmor", "util-linux",
    ))


def test_debian_helper_does_not_call_apt_when_complete(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "dpkg-query", "#!/bin/bash\necho 'install ok installed'\n")
    _executable(bin_dir / "apt-get", f'#!/bin/bash\necho "$*" >> "{calls}"\n')

    env = _debian_env(bin_dir, tmp_path)
    result = subprocess.run(["bash", str(DEBIAN_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert not calls.exists()
