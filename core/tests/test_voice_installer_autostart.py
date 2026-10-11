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


def test_existing_stt_container_without_whisper_is_repaired() -> None:
    """Echter Fund (hh-instcore + hydratest, 11.10.2026): Brach die Erstinstallation nach `incus launch` ab (apt ohne
    Netz), blieb ein leerer STT-Container zurück. Jeder weitere Lauf sah „existiert bereits“ und übersprang die
    Whisper-Installation – der incus-Proxy meldete Port 10300 trotzdem offen. Wie bei Piper: fehlt das Programm,
    wird es nachinstalliert, egal ob der Container neu ist."""
    text = SCRIPT.read_text()
    assert 'test -x /opt/wyoming/bin/wyoming-faster-whisper' in text
    check = text.index('test -x /opt/wyoming/bin/wyoming-faster-whisper')
    install = text.index('pip install wyoming-faster-whisper')
    launch_else = text.index("STT-Container '$CT_NAME' existiert bereits")
    assert check < install
    # Die Installation steht nicht mehr nur im Zweig „Container neu angelegt“.
    assert not (text.rindex('\nif ! incus list', 0, install) < install < launch_else)


def test_stt_health_wait_needs_a_real_answer(tmp_path) -> None:
    """Gleicher Fund: `echo | nc` galt schon als Erfolg, wenn nur der incus-Proxy annimmt. Beide Warteschleifen fragen
    jetzt den Wyoming-Dienst – _wyoming_ok wird hier echt gegen ein Ersatz-nc ausgeführt."""
    import re
    import subprocess
    text = SCRIPT.read_text()
    stt = text[text.index('log "Warte auf STT'):text.index('if [ "$ready" = "0" ]')]
    tts = text[text.index('log "Warte auf TTS'):text.index('if [ "$tts_ready" = "0" ]')]
    assert '_wyoming_ok "$STT_PORT"' in stt and '_wyoming_ok "$TTS_PORT"' in tts
    assert "nc -w1" not in stt + tts
    fn = re.search(r"^_wyoming_ok\(\) \{.*?^\}", text, re.S | re.M).group(0)
    nc = tmp_path / "nc"
    for answer, expected in (('{"type": "info", "version": "1"}', 0), ("", 1), ("HTTP/1.1 400", 1)):
        nc.write_text(f"#!/bin/sh\ncat >/dev/null\nprintf '%s' '{answer}'\n")
        nc.chmod(0o755)
        r = subprocess.run(["bash", "-c", fn + '\n_wyoming_ok 10300'], env={"PATH": f"{tmp_path}:/usr/bin:/bin"},
                           capture_output=True, text=True, timeout=20)
        assert r.returncode == expected, (answer, r.stderr)


def test_voice_nat_bridge_keeps_dns_for_containers_without_host_dns_server() -> None:
    """Echter Fund (hh-instcore, 11.10.2026): `raw.dnsmasq=port=0` schaltet den DNS der Voice-Bridge ab. Ohne
    Pi-hole & Co. auf dem Host haben die Container dann gar keine Namensauflösung → apt scheitert. port=0 nur
    setzen, wenn ein Host-DNS-Server läuft (wie hh_fix_incus_bridge_dns es für Bestandsbrücken tut)."""
    text = SCRIPT.read_text()
    create = text[text.index('incus network create "$VOICE_NET"'):]
    create = create[:create.index("\n  fi\n")]
    assert "raw.dnsmasq=port=0" not in create.split("\n")[0]
    assert "hh_host_dns_unit" in text


def test_container_net_check_needs_name_resolution() -> None:
    """Echter Fund (hh-instcore, 11.10.2026): _net_ok prüfte nur TCP nach 1.1.1.1:53. Das geht auch, wenn der Container
    keine Namensauflösung hat – ensure_container_net kehrte sofort zurück, apt im Container scheiterte trotzdem."""
    import re
    text = SCRIPT.read_text()
    fn = re.search(r"^_net_ok\(\) \{.*?^\}", text, re.S | re.M)
    fn = fn.group(0) if fn else next(x for x in text.splitlines() if x.startswith("_net_ok()"))
    assert "getent hosts" in fn
