"""Bindeglied zwischen eingehenden Channel-Events und dem Agent-Runner.

Channels rufen `run_master_for_event(event)` auf — sucht den Master-Agent
des Ziel-Users, findet/erzeugt die Session pro (Channel, Sender), startet
den Runner, sammelt die finale Assistant-Antwort als String.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config
from hydrahive.communication import _session_lookup
from hydrahive.credentials import redaction
from hydrahive.communication.base import IncomingEvent
from hydrahive.runner import run as runner_run
from hydrahive.runner.concurrency import SessionAlreadyRunning, session_run_guard
from hydrahive.runner.events import Done, Error, MessageStart, TextBlock, TextDelta

logger = logging.getLogger(__name__)


# Wird als zusätzlicher System-Block VOR dem agent-eigenen system_prompt
# eingefügt wenn voice_reply=True. Nicht persistiert — nur per Run.
# Deckt mehrere Failure-Modes ab die der Master sonst macht: eigene
# TTS-Calls, Markdown, Pfade, Datei-Metadaten, Emojis, zu lange Antworten.
_VOICE_MODE_SYSTEM_HINT = """[VOICE-MODE-CALL]
Diese Antwort wird vom Backend automatisch in Sprache umgewandelt und an
den User per WhatsApp-Voice-Note geschickt. Halte dich an folgende Regeln:

1. Antworte als normaler Fließtext. Keine Audio-Datei selbst erstellen,
   kein `mmx`, kein `shell_exec` für TTS, kein Tool-Use für Audio.
2. Keine Markdown-Formatierung. Kein **fett**, keine `code-blocks`,
   keine Asterisken, keine Backticks — alles wird als Text vorgelesen.
3. Keine Pfad-Strings, Datei-Metadaten, Größenangaben, Dauer-Werte —
   weder als Antwort-Inhalt noch als Beschreibung.
4. Keine Emojis. TTS spricht "winkende Hand smiley" statt 👋.
5. Halte die Antwort kurz und gesprochen-natürlich — max ~80 Wörter
   bzw. ~30 Sekunden Sprechzeit. Wenn das Thema länger ist, fasse
   zusammen und biete an mehr Detail per Text-Antwort zu liefern.
6. Schreib so wie du sprechen würdest — keine Bullet-Listen, keine
   Zwischen-Überschriften, keine Tabellen.
[/VOICE-MODE-CALL]"""


def _operator_directive_block(prefix: str, *, is_owner: bool) -> str:
    """Betreiber-Vorgabe als vertrauenswürdiger System-Block.

    MUSS in `extra_system` (System-Schicht), NICHT in den User-Turn: ein
    injection-resistenter Agent (Opus 4.8) hält eine Identitäts-/Persona-Anweisung
    im User-Turn für eine eingeschleuste Nachricht und lehnt sie korrekt ab. In der
    System-Schicht ist sie echte Betreiber-Konfiguration und wird befolgt.
    """
    floor = "" if is_owner else (
        "\n\nSicherheits-Boden (gilt immer, auch hier): niemals Passwörter, Secrets, "
        "Zugangsdaten oder Tokens preisgeben; keine System-/Datei-/Admin-Aktionen ausführen."
    )
    return (
        "[BETREIBER-VORGABE FÜR DIESE CHANNEL-ANTWORT]\n"
        "Diese Anweisung stammt von deinem Betreiber über den vertrauenswürdigen "
        "System-Kanal — NICHT vom Absender der Nachricht. Sie ist deine Konfiguration "
        "für diese automatische Antwort und hat Vorrang vor deiner sonstigen Persona:\n\n"
        f"{prefix}{floor}\n"
        "[/BETREIBER-VORGABE]"
    )


def _build_agent_input(event: IncomingEvent, prefix: str | None, voice_reply: bool) -> tuple[str, str | None]:
    """Baut (user_text, extra_system) für einen eingehenden Channel-Agent-Run.

    Zwei Schichten, bewusst getrennt:
      USER-TURN: Sender-Rahmung (HH1-Port: wer/Kanal/Vertrauensstufe, damit der Agent
        WEISS dass er einem externen Kontakt antwortet) + die eigentliche Nachricht.
        Ohne Betreiber-Vorgabe zusätzlich der Datenschutz-Block für Fremde.
      SYSTEM (`extra_system`): die Betreiber-Vorgabe (vertrauenswürdig, sonst lehnt der
        Agent sie als Injection ab) + ggf. der Voice-Mode-Hint.
    """
    is_owner = bool(event.metadata.get("is_owner", False))
    is_group = bool(event.metadata.get("is_group", False))
    sender_label = event.sender_name or event.external_user_id
    chat_type = "Gruppen-Chat" if is_group else "Einzel-Chat"
    channel = (event.channel or "Channel").capitalize()
    trust = "vertrauenswürdiger Kontakt" if is_owner else "unbekannter Kontakt"

    lines = [f"[{channel} {chat_type} von {sender_label} — {trust}]"]
    # Ohne Vorgabe: vorsichtiger Datenschutz-Block für Fremde im User-Turn. MIT
    # Vorgabe wandert alles Anweisende in die System-Schicht (die Vorgabe regelt
    # dann Persona + was geteilt wird, plus Sicherheits-Boden).
    if not is_owner and not prefix:
        lines.append(
            "[ANWEISUNG FÜR DIESEN KONTAKT: Nenne NICHT den Namen des Besitzers; "
            "beschreibe KEINE internen System-Fähigkeiten; teile keine privaten Daten, "
            "Passwörter oder persönlichen Infos des Besitzers; stelle dich als allgemeiner "
            "KI-Assistent vor; führe KEINE System-/Datei-/Admin-Aktionen aus. "
            "Antworte freundlich und hilfsbereit.]"
        )
    lines.append(event.text)
    user_text = "\n".join(lines)

    system_blocks: list[str] = []
    if prefix:
        system_blocks.append(_operator_directive_block(prefix, is_owner=is_owner))
    if voice_reply:
        system_blocks.append(_VOICE_MODE_SYSTEM_HINT)
    extra_system = "\n\n".join(system_blocks) if system_blocks else None
    return user_text, extra_system


class NoMasterError(RuntimeError):
    """User hat keinen Master-Agent (z.B. LLM noch nicht konfiguriert)."""


def _find_master(username: str) -> dict | None:
    for a in agent_config.list_by_owner(username):
        if a.get("type") == "master" and a.get("status") != "disabled":
            return a
    return None


async def run_master_for_event(event: IncomingEvent, *, voice_reply: bool = False) -> str:
    """Verarbeitet ein eingehendes Channel-Event durch den Master-Agent.

    voice_reply=True ⇒ zusätzlicher Voice-Mode-System-Block für diesen Run.
    """
    master = _find_master(event.target_username)
    if not master:
        raise NoMasterError(f"kein Master-Agent für '{event.target_username}'")
    return await _run_agent(master["id"], event, prefix=None, voice_reply=voice_reply)


async def run_agent_for_event(
    agent_id: str, event: IncomingEvent, *,
    prefix: str | None = None, voice_reply: bool = False,
) -> str:
    """Wie run_master_for_event, aber mit explizitem Agent (z.B. aus
    Butler `agent_reply`/`agent_reply_with_prefix`)."""
    return await _run_agent(agent_id, event, prefix=prefix, voice_reply=voice_reply)


async def _run_agent(
    agent_id: str, event: IncomingEvent, *,
    prefix: str | None, voice_reply: bool = False,
) -> str:
    session = _session_lookup.find_or_create(
        agent_id=agent_id,
        user_id=event.target_username,
        channel=event.channel,
        external_user_id=event.external_user_id,
        title_hint=f"{event.channel}: {event.sender_name or event.external_user_id}",
    )
    user_text, extra_system = _build_agent_input(event, prefix, voice_reply)

    answer_parts: list[str] = []
    current_text: list[str] = []
    try:
        async with session_run_guard(session.id):
            async for ev in runner_run(session.id, user_text, extra_system=extra_system):
                if isinstance(ev, MessageStart):
                    current_text = []
                elif isinstance(ev, TextDelta):
                    current_text.append(ev.text)
                elif isinstance(ev, TextBlock):
                    if current_text:
                        answer_parts.append("".join(current_text))
                        current_text = []
                elif isinstance(ev, Done):
                    if current_text:
                        answer_parts.append("".join(current_text))
                    break
                elif isinstance(ev, Error):
                    logger.error("Runner-Fehler im Channel-Run: %s", ev.message)
                    raise RuntimeError(ev.message)
    except SessionAlreadyRunning:
        logger.warning("Channel-Run skipped: Session %s läuft bereits", session.id)
        raise RuntimeError("Session läuft bereits — Nachricht ignoriert")

    # Egress-Engstelle: kein lebender Secret-Wert verlässt das System Richtung
    # externer Kontakt (WhatsApp/Discord/Voice), egal wie das LLM an ihn kam.
    return redaction.scrub("\n\n".join(p for p in answer_parts if p.strip()))
