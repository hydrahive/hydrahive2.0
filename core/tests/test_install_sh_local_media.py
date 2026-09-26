"""install.sh: Lokale Bild-/Videogenerierung nur auf ausdrücklichen Wunsch.

Vorher: Phase 4c lief bei jeder NVIDIA-GPU automatisch (~33 GB) und brach
bei einem Fehler die ganze Installation ab.
"""
from __future__ import annotations

from pathlib import Path

INSTALL = Path(__file__).resolve().parents[2] / "installer" / "install.sh"


def _text() -> str:
    return INSTALL.read_text()


def test_local_media_is_a_wizard_choice_defaulting_to_no() -> None:
    assert "prompt_component HH_INSTALL_LOCAL_MEDIA n " in _text()


def test_choice_is_persisted_in_install_conf() -> None:
    text = _text()
    conf_vars = text[text.index("CONF_VARS=("):text.index(")", text.index("CONF_VARS=("))]
    assert "HH_INSTALL_LOCAL_MEDIA" in conf_vars


def test_module_only_runs_when_chosen_and_sets_marker() -> None:
    text = _text()
    call = text.index('bash "$INSTALLER_DIR/modules/72-local-media.sh"')
    guard = text.rindex('if [ "${HH_INSTALL_LOCAL_MEDIA:-no}" = "yes" ]', 0, call)
    assert call - guard < 200
    after = text[call:call + 300]
    assert 'local-media.enabled' in after
    assert "err_soft" in after and '  err "' not in after
