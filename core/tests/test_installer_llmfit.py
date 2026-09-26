from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).parents[2]
MODULE = ROOT / "installer" / "modules" / "35-llmfit.sh"


def test_llmfit_installer_is_pinned_and_checksum_verified():
    script = MODULE.read_text()
    assert 'LLMFIT_VERSION="1.1.12"' in script
    assert "6a97338862c87e497c844ccd29a16512a147335631c179744b4f6cc87a36ead1" in script
    assert "2407cfc625aaa4823d4eb994533b15b6f71acda2646b18368a75313462962610" in script
    assert "sha256sum --check --status" in script
    assert "--proto '=https'" in script
    assert "curl" in script
    assert re.search(r"curl[^\n]*\|\s*(?:ba)?sh", script) is None


def test_install_and_update_call_optional_llmfit_module():
    assert "modules/35-llmfit.sh" in (ROOT / "installer" / "install.sh").read_text()
    assert "modules/35-llmfit.sh" in (ROOT / "installer" / "update.sh").read_text()


def test_llmfit_shell_scripts_have_valid_syntax():
    for script in (MODULE, ROOT / "installer" / "install.sh", ROOT / "installer" / "update.sh"):
        subprocess.run(["bash", "-n", str(script)], check=True)
