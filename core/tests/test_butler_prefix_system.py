"""Butler-Vorgabe (agent_reply_with_prefix) muss als System-Anweisung ankommen,
nicht im User-Turn (sonst wehrt die Injection-Abwehr des Agenten sie ab).

Bug: _agent_glue klebte `[BUTLER-VORGABE: ...]` vor die Sender-Nachricht und gab
das als User-Input an den Runner — der Agent behandelte die Operator-Vorgabe als
Prompt-Injection und lehnte ab. Fix: prefix → extra_system (vertrauenswürdig).
"""
from __future__ import annotations

# hydrahive-Imports lazy in den Tests (settings.data_dir-Freeze-Gotcha).


def test_prefix_goes_to_system_not_user():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, extra_system = _build_agent_input("Test", "Antworte als Joshua", voice_reply=False)
    # User-Turn bleibt die rohe Sender-Nachricht — KEIN Prepend.
    assert user_text == "Test"
    assert extra_system is not None
    assert "Antworte als Joshua" in extra_system
    assert "BUTLER-VORGABE" in extra_system


def test_no_prefix_no_voice_is_plain():
    from hydrahive.communication._agent_glue import _build_agent_input
    user_text, extra_system = _build_agent_input("Hallo", None, voice_reply=False)
    assert user_text == "Hallo"
    assert extra_system is None


def test_voice_only_uses_voice_hint():
    from hydrahive.communication._agent_glue import _build_agent_input, _VOICE_MODE_SYSTEM_HINT
    user_text, extra_system = _build_agent_input("Hi", None, voice_reply=True)
    assert user_text == "Hi"
    assert extra_system == _VOICE_MODE_SYSTEM_HINT


def test_prefix_and_voice_both_in_system():
    from hydrahive.communication._agent_glue import _build_agent_input
    _user, extra_system = _build_agent_input("x", "sei kurz", voice_reply=True)
    assert "sei kurz" in extra_system
    assert "VOICE-MODE-CALL" in extra_system
