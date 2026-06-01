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


def test_butler_vorgabe_is_operator_directive():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, _ = _build_agent_input(_event(), "Antworte als Joshua", voice_reply=False)
    assert "Antworte als Joshua" in user_text
    assert "Betreiber" in user_text  # als Betreiber-Direktive gerahmt, nicht als Sender-Text


def test_vorgabe_overrides_privacy_guard_for_unknown_contact():
    # Bug: bei Fremden + Vorgabe überstimmte der generische Datenschutz-Block die
    # Betreiber-Vorgabe (Agent sagte "ich bin KI-Assistent" statt der Persona aus
    # der Vorgabe). Fix: Vorgabe gewinnt, nur harter Sicherheits-Boden bleibt.
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, _ = _build_agent_input(
        _event(is_owner=False), "Du bist Joshua, stell dich mit Namen vor", voice_reply=False)
    assert "Du bist Joshua" in user_text                     # Vorgabe da
    assert "stelle dich als allgemeiner" not in user_text    # generische Persona NICHT erzwungen
    assert "Nenne NICHT den Namen des Besitzers" not in user_text
    assert "SICHERHEITS-BODEN" in user_text                  # harter Boden bleibt
    assert "Passwörter" in user_text and "System-/Datei-/Admin" in user_text


def test_voice_hint_in_extra_system():
    from hydrahive.communication._agent_glue import _build_agent_input, _VOICE_MODE_SYSTEM_HINT
    _user, extra_system = _build_agent_input(_event(), None, voice_reply=True)
    assert extra_system == _VOICE_MODE_SYSTEM_HINT
