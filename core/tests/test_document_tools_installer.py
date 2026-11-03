from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAC_HELPER = ROOT / "installer/lib/mac-document-tools.sh"
MAC_DEPS = ROOT / "installer/modules-mac/00-deps.sh"
MAC_UPDATE = ROOT / "installer/update-mac.sh"
DEBIAN_HELPER = ROOT / "installer/lib/debian-document-tools.sh"
DEBIAN_DEPS = ROOT / "installer/modules/00-deps.sh"
DEBIAN_UPDATE = ROOT / "installer/update.sh"


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_mac_installer_and_update_use_role_aware_document_helper() -> None:
    helper = MAC_HELPER.read_text(encoding="utf-8")
    deps = MAC_DEPS.read_text(encoding="utf-8")
    update = MAC_UPDATE.read_text(encoding="utf-8")

    assert "mac-roles.sh" in helper
    assert "as_brew" in helper
    assert {"poppler", "tesseract", "tesseract-lang"} <= set(helper.replace('"', "").split())
    assert "mac-document-tools.sh" in deps
    assert update.index("git pull --ff-only") < update.index("mac-document-tools.sh")


def test_mac_helper_installs_only_missing_formulas(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "brew", f'''#!/bin/bash
if [ "$1" = list ]; then [ "$3" = poppler ] && exit 0; exit 1; fi
if [ "$1" = install ]; then echo "$2" >> "{calls}"; exit 0; fi
exit 0
''')
    for name in ("pdfinfo", "pdftotext", "pdftoppm"):
        _executable(bin_dir / name, "#!/bin/bash\nexit 0\n")
    _executable(bin_dir / "tesseract", "#!/bin/bash\n[ \"$1\" = --list-langs ] && echo deu\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HH_BREW": str(bin_dir / "brew"),
           "HH_BREW_USER": os.environ.get("USER", "root"), "HH_USER": os.environ.get("USER", "root")}

    result = subprocess.run(["bash", str(MAC_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["tesseract", "tesseract-lang"]


def test_debian_first_install_and_update_include_document_packages() -> None:
    deps = DEBIAN_DEPS.read_text(encoding="utf-8")
    update = DEBIAN_UPDATE.read_text(encoding="utf-8")
    packages = {"poppler-utils", "tesseract-ocr", "tesseract-ocr-deu", "tesseract-ocr-eng"}

    assert all(package in deps for package in packages)
    assert "debian-document-tools.sh" in update
    assert update.index("git pull") < update.index("debian-document-tools.sh")


def test_debian_helper_is_idempotent_and_installs_missing_packages(tmp_path: Path) -> None:
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls"
    bin_dir.mkdir()
    _executable(bin_dir / "dpkg-query", "#!/bin/bash\ncase \"$*\" in *poppler-utils*) echo 'install ok installed';; *) exit 1;; esac\n")
    _executable(bin_dir / "apt-get", f'#!/bin/bash\necho "$*" >> "{calls}"\n')
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}

    result = subprocess.run(["bash", str(DEBIAN_HELPER)], env=env, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    lines = calls.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "update"
    assert lines[1].startswith("install -y ")
    assert "poppler-utils" not in lines[1]
    assert all(package in lines[1] for package in ("tesseract-ocr", "tesseract-ocr-deu", "tesseract-ocr-eng"))
