"""Bindeglied zwischen eingehenden Channel-Events und dem Agent-Runner.

Channels rufen `run_master_for_event(event)` auf — sucht den Master-Agent
des Ziel-Users, findet/erzeugt die Session pro (Channel, Sender), startet
den Runner, sammelt die finale Assistant-Antwort als String.
"""
from __future__ import annotations

import logging

from hydrahive.agents import config as agent_config
from hydrahive.communication import _session_lookup
from hydrahive.communication.base import IncomingEvent
from hydrahive.runner import run as runner_run
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
    user_text = event.text
    if prefix:
        user_text = f"[BUTLER-VORGABE: {prefix}]\n\n{event.text}"

    extra_system = _VOICE_MODE_SYSTEM_HINT if voice_reply else None

    answer_parts: list[str] = []
    current_text: list[str] = []
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

    return "\n\n".join(p for p in answer_parts if p.strip())
