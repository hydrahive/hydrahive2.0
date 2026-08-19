from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "modules" / "55-voice.sh"
UPDATE_SCRIPT = INSTALLER / "update.sh"


def test_both_voice_containers_enable_boot_autostart() -> None:
    text = SCRIPT.read_text()

    assert 'incus config set "$CT_NAME" boot.autostart true' in text
    assert 'incus config set "$CT_TTS" boot.autostart true' in text


def test_autostart_is_set_before_health_waits() -> None:
    text = SCRIPT.read_text()

    stt_autostart = text.index('incus config set "$CT_NAME" boot.autostart true')
    stt_wait = text.index('log "Warte auf STT')
    tts_autostart = text.index('incus config set "$CT_TTS" boot.autostart true')
    tts_wait = text.index('log "Warte auf TTS')
    assert stt_autostart < stt_wait
    assert tts_autostart < tts_wait


def test_update_migrates_existing_voice_containers_to_autostart() -> None:
    text = UPDATE_SCRIPT.read_text()

    assert "for voice_container in hydrahive2-stt hydrahive2-tts" in text
    assert 'incus config set "$voice_container" boot.autostart true' in text
    assert 'incus start "$voice_container"' in text
