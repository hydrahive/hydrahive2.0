"""Voice/STT-Verarbeitung für WA-Incoming: Decode → Transcribe → Error-Handling."""
from __future__ import annotations

import asyncio
import base64
import logging

logger = logging.getLogger(__name__)


async def process_voice(
    *,
    media_type: str | None,
    media_data: str | None,
    media_mime: str | None,
    media_error: str | None,
    stt_language: str | None,
    target_username: str,
) -> tuple[str | None, str | None]:
    """Returns (transcribed_text_or_None, error_message_or_None).

    - success: (transcript, None)
    - error: (None, error_message)
    """
    if media_type == "audio_failed":
        logger.warning("WA voice download failed user=%s: %s", target_username, media_error)
        return None, (
            "Deine Sprachnachricht konnte nicht heruntergeladen werden. "
            "Bitte schick sie nochmal oder als Text. 🙏"
        )

    if media_type == "audio" and media_data:
        try:
            from hydrahive.voice.stt import transcribe_bytes
            audio_bytes = base64.b64decode(media_data)
            stt_lang = stt_language if stt_language and stt_language != "auto" else None
            transcript = await transcribe_bytes(
                audio_bytes, mime=media_mime or "audio/ogg", language=stt_lang,
            )
            if not transcript:
                return None, (
                    "Ich konnte in deiner Sprachnachricht nichts verstehen. "
                    "Bitte nochmal aufnehmen oder als Text. 🙏"
                )
            logger.info("WA voice transcribed user=%s len=%d → %r",
                        target_username, len(audio_bytes), transcript[:80])
            return transcript, None
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError) as e:
            logger.warning("WA voice STT unreachable: %s", e)
            return None, (
                "Der Sprache-zu-Text-Service ist gerade nicht erreichbar. "
                "Bitte schick mir die Frage als Text."
            )
        except Exception as e:
            logger.exception("WA voice STT fehlgeschlagen: %s", e)
            return None, (
                "Beim Transkribieren deiner Sprachnachricht ist ein Fehler "
                "aufgetreten. Bitte nochmal versuchen oder als Text schicken."
            )

    return None, None  # kein Voice-Content → Text-Pfad läuft normal


async def send_voice_or_text(
    ch,
    *,
    answer: str,
    target_username: str,
    external_user_id: str,
    respond_as_voice: bool,
    voice_name: str,
    looks_like_metadata: bool,
) -> bool:
    """Sendet Antwort als Voice oder Text. Returns True wenn voice_metadata_fallback."""
    if respond_as_voice and looks_like_metadata:
        logger.warning("WA voice-mode: Antwort sieht wie Datei-Metadaten aus, "
                       "fallback auf Text. Antwort: %r", answer[:200])
        try:
            await ch.send(target_username, external_user_id, answer)
        except Exception as e:
            logger.warning("Voice-Fallback-Text-Send fehlgeschlagen: %s", e)
        return True  # voice_metadata_fallback

    try:
        if respond_as_voice:
            from hydrahive.voice.tts import synthesize_to_ogg
            clip = await synthesize_to_ogg(answer, voice=voice_name)
            await ch.send_audio(
                target_username, external_user_id,
                base64.b64encode(clip.ogg_bytes).decode(),
                seconds=clip.seconds,
                waveform_b64=base64.b64encode(clip.waveform).decode(),
            )
        else:
            await ch.send(target_username, external_user_id, answer)
    except Exception as e:
        logger.exception("WhatsApp-Antwort konnte nicht gesendet werden: %s", e)
        if respond_as_voice:
            try:
                await ch.send(target_username, external_user_id, answer)
            except Exception:
                pass
    return False
