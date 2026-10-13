"""Voice-Bridge beim Neubau des Kern-venv (Spec docs/specs/python-314-umstieg.md).

hydra-voice-bridge.service läuft mit /opt/hydrahive2/.venv/bin/python. Baut
update.sh das Kern-venv neu (3.12 → 3.14), stoppt es bisher nur hydrahive2.
Die Bridge liefe währenddessen mit gelöschten Paketen weiter und danach mit
dem alten Stand im Speicher (Befund 6.8.: 24 gelöschte Dateien gemappt).
"""
from __future__ import annotations

from pathlib import Path

UPDATE = Path(__file__).resolve().parents[2] / "installer" / "update.sh"


def _text() -> str:
    return UPDATE.read_text()


def test_bridge_is_stopped_before_core_venv_rebuild() -> None:
    text = _text()
    ensure = text.index('hh_ensure_python_venv \\\n  "$HH_REPO_DIR/.venv"')
    before = text[text.rindex("\n\n", 0, ensure - 200):ensure]

    assert "hydra-voice-bridge.service" in before
    assert "HH_VENV_PROBE" in before or "hh_venv_needs_rebuild" in before
    assert "systemctl stop hydra-voice-bridge.service" in before


def test_bridge_restarts_after_core_restart_only_if_present() -> None:
    text = _text()
    core_restart = text.index("systemctl restart hydrahive2.service\n\nsleep 2")
    after = text[core_restart:]

    # try-restart: startet nur, was es gibt und schon lief; plus der Fall
    # „vor dem Neubau gestoppt“ → gezielt wieder starten.
    assert "hydra-voice-bridge.service" in after
    assert 'if [ "$HH_BRIDGE_STOPPED" = "1" ]' in after
    assert "systemctl start hydra-voice-bridge.service" in after
    assert "systemctl try-restart hydra-voice-bridge.service" in after
