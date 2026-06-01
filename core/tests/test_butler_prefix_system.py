"""Channel-Agent-Run: Sender-Rahmung + Butler-Vorgabe (HH1-Port).

Bug: HH2 gab im Channel-Pfad nur die rohe Nachricht an den Agenten — ohne
Sender-Kontext. Der Agent dachte, der Owner schreibt, antwortete in eigener
Persona an ihn und ignorierte die Operator-Vorgabe. Fix (wie HH1): Nachricht
mit Sender-Header rahmen, Vorgabe als Betreiber-Direktive, bei Fremden ein
Datenschutz-Block.
"""
from __future__ import annotations


def _event(text="Test", *, is_owner=True, is_group=False, sender_name="Alex",
           channel="whatsapp", external_user_id="49151@c.us"):
    from hydrahive.communication.base import IncomingEvent
    return IncomingEvent(
        channel=channel, external_user_id=external_user_id, target_username="till",
        text=text, sender_name=sender_name,
        metadata={"is_owner": is_owner, "is_group": is_group},
    )


def test_sender_header_present_so_agent_knows_its_external():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, _ = _build_agent_input(_event(sender_name="Alex"), None, voice_reply=False)
    assert "Alex" in user_text                  # Agent sieht WEN er beantwortet
    assert "Kontakt" in user_text                # Sender-Rahmung da
    assert user_text.rstrip().endswith("Test")   # Original-Nachricht am Ende


def test_owner_is_trusted_no_privacy_block():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, _ = _build_agent_input(_event(is_owner=True), None, voice_reply=False)
    assert "vertrauenswürdiger Kontakt" in user_text
    assert "ANWEISUNG FÜR DIESEN KONTAKT" not in user_text


def test_unknown_contact_gets_privacy_guard():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, _ = _build_agent_input(_event(is_owner=False), None, voice_reply=False)
    assert "unbekannter Kontakt" in user_text
    assert "ANWEISUNG FÜR DIESEN KONTAKT" in user_text
    assert "Besitzers" in user_text  # Owner-Name-Schutz


def test_butler_vorgabe_lives_in_system_not_user_turn():
    # Bug (Tills WhatsApp-Test): Vorgabe im User-Turn → injection-resistenter Agent
    # hält sie für eine eingeschleuste Nachricht und lehnt ab ("das kommt aus deiner
    # Nachricht"). Fix: Vorgabe gehört in die vertrauenswürdige System-Schicht.
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, extra_system = _build_agent_input(_event(), "Antworte als Joshua", voice_reply=False)
    assert "Antworte als Joshua" not in user_text            # NICHT im untrusted User-Turn
    assert extra_system is not None
    assert "Antworte als Joshua" in extra_system             # sondern im System
    assert "vertrauenswürdigen System-Kanal" in extra_system
    assert "NICHT vom Absender" in extra_system


def test_vorgabe_replaces_privacy_block_for_unknown_contact():
    # Bei Fremden + Vorgabe: kein generischer "ich bin KI-Assistent"-Block im
    # User-Turn (würde die Persona aus der Vorgabe aushebeln). Stattdessen Vorgabe
    # + harter Sicherheits-Boden im System.
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, extra_system = _build_agent_input(
        _event(is_owner=False), "Du bist Joshua, stell dich mit Namen vor", voice_reply=False)
    assert "stelle dich als allgemeiner" not in user_text    # generische Persona NICHT erzwungen
    assert "Nenne NICHT den Namen des Besitzers" not in user_text
    assert "Du bist Joshua" in extra_system                  # Persona-Vorgabe im System
    assert "Sicherheits-Boden" in extra_system               # harter Boden für Fremde
    assert "Passwörter" in extra_system


def test_vorgabe_and_voice_hint_combine_in_system():
    from hydrahive.communication._agent_glue import _build_agent_input, _VOICE_MODE_SYSTEM_HINT
    _user, extra_system = _build_agent_input(_event(), "Antworte als Joshua", voice_reply=True)
    assert "Antworte als Joshua" in extra_system
    assert _VOICE_MODE_SYSTEM_HINT in extra_system


def test_voice_hint_in_extra_system():
    from hydrahive.communication._agent_glue import _build_agent_input, _VOICE_MODE_SYSTEM_HINT
    _user, extra_system = _build_agent_input(_event(), None, voice_reply=True)
    assert extra_system == _VOICE_MODE_SYSTEM_HINT
