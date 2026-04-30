"""Communication-API — Channel-Liste, WhatsApp-Endpunkte, Bridge-Push."""
from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.communication import all_channels, get, handle_incoming
from hydrahive.communication.base import ChannelStatus, IncomingEvent
from hydrahive.communication.whatsapp import config as wa_config
from hydrahive.communication.whatsapp import filter as wa_filter
from hydrahive.communication.whatsapp.process import ensure_secret
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/communication", tags=["communication"])


# Belt-and-Braces für Voice-Mode: wenn der Master den System-Hint ignoriert
# und doch Datei-Metadaten zurückliefert, wollen wir das nicht TTSen.
_METADATA_HINTS = re.compile(
    r"(\.mp3|\.wav|\.ogg|\.m4a|"           # Audio-File-Extensions
    r"\bdauer\b|\bduration\b|"             # Dauer-Wörter
    r"\bgr(ö|oe)ße\b|\bsize\b|"            # Größe
    r"\bgespeichert\b|\bstored at\b|"      # Speicherort
    r"\b\d+(?:\.\d+)?\s*(?:kb|mb|gb)\b|"   # Größen-Einheiten
    r"\b\d+(?:[.,]\d+)?\s*(?:sec|sek|min|hour|stund|second|minut)\w*\b)",  # Zeit-Einheiten
    re.IGNORECASE,
)


def _looks_like_metadata(answer: str) -> bool:
    """Heuristik: enthält die Antwort Datei-Metadaten-Strings? Mehrere Treffer
    deuten darauf hin dass der Master 'Datei erstellt: X kb, Y sec' erzählt
    statt den eigentlichen Inhalt geliefert hat. False positives möglich,
    aber bei aktivem Voice-Mode ist die Toleranz niedrig."""
    if not answer:
        return False
    hits = len(_METADATA_HINTS.findall(answer))
    return hits >= 2


def _status_dict(s: ChannelStatus) -> dict:
    return {
        "connected": s.connected,
        "state": s.state,
        "detail": s.detail,
        "qr_data_url": s.qr_data_url,
    }


@router.get("/channels")
async def list_channels(_=Depends(require_auth)) -> list[dict]:
    return [{"name": c.name, "label": c.label} for c in all_channels()]


@router.get("/whatsapp/status")
async def wa_status(auth=Depends(require_auth)) -> dict:
    ch = get("whatsapp")
    if not ch:
        raise coded(503, "channel_unavailable", channel="whatsapp")
    username, _ = auth
    return _status_dict(await ch.status(username))


@router.post("/whatsapp/connect")
async def wa_connect(auth=Depends(require_auth)) -> dict:
    ch = get("whatsapp")
    if not ch:
        raise coded(503, "channel_unavailable", channel="whatsapp")
    username, _ = auth
    return _status_dict(await ch.connect(username))


@router.post("/whatsapp/disconnect")
async def wa_disconnect(auth=Depends(require_auth)) -> dict:
    ch = get("whatsapp")
    if not ch:
        raise coded(503, "channel_unavailable", channel="whatsapp")
    username, _ = auth
    await ch.disconnect(username)
    return {"ok": True}


@router.get("/whatsapp/config")
async def wa_get_config(auth=Depends(require_auth)) -> dict:
    username, _ = auth
    cfg = wa_config.load(username)
    return _config_dict(cfg)


@router.put("/whatsapp/config")
async def wa_put_config(payload: dict, auth=Depends(require_auth)) -> dict:
    username, _ = auth
    cfg = wa_config.WhatsAppConfig(
        private_chats_enabled=bool(payload.get("private_chats_enabled", True)),
        group_chats_enabled=bool(payload.get("group_chats_enabled", False)),
        require_keyword=str(payload.get("require_keyword", "") or ""),
        owner_numbers=list(payload.get("owner_numbers", []) or []),
        allowed_numbers=list(payload.get("allowed_numbers", []) or []),
        blocked_numbers=list(payload.get("blocked_numbers", []) or []),
    )
    saved = wa_config.save(username, cfg)
    return _config_dict(saved)


def _config_dict(cfg: wa_config.WhatsAppConfig) -> dict:
    return {
        "private_chats_enabled": cfg.private_chats_enabled,
        "group_chats_enabled": cfg.group_chats_enabled,
        "require_keyword": cfg.require_keyword,
        "owner_numbers": cfg.owner_numbers,
        "allowed_numbers": cfg.allowed_numbers,
        "blocked_numbers": cfg.blocked_numbers,
    }


# ---------------------------------------------------------- bridge → backend


@router.post("/whatsapp/incoming")
async def wa_incoming(
    payload: dict,
    x_hh_bridge_secret: Annotated[str | None, Header(alias="X-HH-Bridge-Secret")] = None,
) -> dict:
    expected = ensure_secret(settings.whatsapp_bridge_secret_file)
    if x_hh_bridge_secret != expected:
        raise HTTPException(status_code=401, detail="bad_secret")

    target_username = payload.get("target_username")
    external_user_id = payload.get("external_user_id")
    text = payload.get("text", "") or ""
    is_group = bool(payload.get("is_group", False))
    participant = payload.get("participant")
    media_type = payload.get("media_type")
    media_mime = payload.get("media_mime")
    media_data = payload.get("media_data")  # base64
    media_error = payload.get("media_error")

    if not target_username or not external_user_id:
        raise HTTPException(status_code=400, detail="missing_fields")
    if not text and media_type not in ("audio", "audio_failed"):
        raise HTTPException(status_code=400, detail="missing_fields")

    # Pre-Filter VOR STT: Sender-Check ohne Keyword. Spart STT-Ressourcen für
    # geblockte Sender und vermeidet Info-Leak (geblockter User kriegt sonst
    # die "Voice-download-failed"-Antwort und weiß: System ist da).
    cfg = wa_config.load(target_username)
    sender_for_filter = participant if (is_group and participant) else external_user_id
    pre_decision = wa_filter.evaluate(
        cfg=cfg, sender_jid=sender_for_filter, is_group=is_group,
        text="", skip_keyword=True,
    )
    if not pre_decision.accepted:
        logger.info("WhatsApp pre-filter (%s): user=%s sender=%s",
                    pre_decision.reason, target_username, sender_for_filter)
        return {"ok": True, "filtered": pre_decision.reason}

    # Voice-Failure-Pfad: Bridge konnte nicht downloaden ODER STT crasht.
    # Wir antworten direkt mit Text — Master-Agent NICHT belasten.
    voice_error_msg: str | None = None
    if media_type == "audio_failed":
        voice_error_msg = (
            "Deine Sprachnachricht konnte nicht heruntergeladen werden. "
            "Bitte schick sie nochmal oder als Text. 🙏"
        )
        logger.warning("WA voice download failed user=%s: %s",
                       target_username, media_error)
    elif media_type == "audio" and media_data:
        try:
            from hydrahive.voice.stt import transcribe_bytes
            audio_bytes = base64.b64decode(media_data)
            stt_lang = cfg.stt_language if cfg.stt_language and cfg.stt_language != "auto" else None
            transcript = await transcribe_bytes(
                audio_bytes, mime=media_mime or "audio/ogg",
                language=stt_lang,
            )
            if not transcript:
                voice_error_msg = (
                    "Ich konnte in deiner Sprachnachricht nichts verstehen. "
                    "Bitte nochmal aufnehmen oder als Text. 🙏"
                )
            else:
                text = transcript
                logger.info("WA voice transcribed user=%s len=%d → %r",
                            target_username, len(audio_bytes), text[:80])
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError) as e:
            logger.warning("WA voice STT unreachable: %s", e)
            voice_error_msg = (
                "Der Sprache-zu-Text-Service ist gerade nicht erreichbar. "
                "Bitte schick mir die Frage als Text."
            )
        except Exception as e:
            logger.exception("WA voice STT fehlgeschlagen: %s", e)
            voice_error_msg = (
                "Beim Transkribieren deiner Sprachnachricht ist ein Fehler "
                "aufgetreten. Bitte nochmal versuchen oder als Text schicken."
            )

    if voice_error_msg:
        ch = get("whatsapp")
        if ch:
            try:
                await ch.send(target_username, external_user_id, voice_error_msg)
            except Exception as e:
                logger.warning("Voice-Error-Reply konnte nicht gesendet werden: %s", e)
        return {"ok": True, "voice_error": True}

    # Post-Filter: jetzt mit (ggf. transkribiertem) Text — der Keyword-Check
    # läuft jetzt erst, alle Sender-Checks sind oben schon durchgelaufen.
    decision = wa_filter.evaluate(
        cfg=cfg, sender_jid=sender_for_filter, is_group=is_group, text=text,
    )
    if not decision.accepted:
        logger.info(
            "WhatsApp gefiltert (%s): user=%s sender=%s",
            decision.reason, target_username, sender_for_filter,
        )
        return {"ok": True, "filtered": decision.reason}

    event = IncomingEvent(
        channel="whatsapp",
        external_user_id=external_user_id,
        target_username=target_username,
        text=text,
        sender_name=payload.get("sender_name"),
        metadata={"is_group": is_group, "is_owner": decision.is_owner,
                  "participant": participant, "voice_mode": cfg.respond_as_voice},
    )
    answer = await handle_incoming(event)
    logger.info(
        "WA incoming user=%s sender=%s text=%r → answer=%r",
        target_username, sender_for_filter, text[:60],
        (answer[:100] if answer else None),
    )
    if answer:
        ch = get("whatsapp")
        if ch:
            # Sanity-Check: bei aktivem Voice-Mode prüfen ob die Antwort wie
            # Datei-Metadaten aussieht (Master hat den Hint ignoriert und
            # eigenmächtig mmx-Output zurückgegeben). In dem Fall nicht
            # TTSen — sonst hört der User '425 kb mp3 Dauer 12 Sekunden'.
            if cfg.respond_as_voice and _looks_like_metadata(answer):
                logger.warning(
                    "WA voice-mode: Antwort sieht wie Datei-Metadaten aus, "
                    "fallback auf Text. Antwort: %r", answer[:200],
                )
                try:
                    await ch.send(target_username, external_user_id, answer)
                except Exception as e:
                    logger.warning("Voice-Fallback-Text-Send fehlgeschlagen: %s", e)
                return {"ok": True, "voice_metadata_fallback": True}

            try:
                if cfg.respond_as_voice:
                    from hydrahive.voice.tts import synthesize_to_ogg
                    clip = await synthesize_to_ogg(answer, voice=cfg.voice_name)
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
                # Fallback: als Text senden falls Voice scheitert
                if cfg.respond_as_voice:
                    try:
                        await ch.send(target_username, external_user_id, answer)
                    except Exception:
                        pass
    return {"ok": True}
