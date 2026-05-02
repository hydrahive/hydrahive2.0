from __future__ import annotations

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from hydrahive.api.routes._wa_voice import process_voice, send_voice_or_text
from hydrahive.communication import get, handle_incoming
from hydrahive.communication.base import IncomingEvent
from hydrahive.communication.whatsapp import config as wa_config
from hydrahive.communication.whatsapp import filter as wa_filter
from hydrahive.communication.whatsapp.process import ensure_secret
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/communication", tags=["communication"])

_METADATA_HINTS = re.compile(
    r"(\.mp3|\.wav|\.ogg|\.m4a|"
    r"\bdauer\b|\bduration\b|"
    r"\bgr(ö|oe)ße\b|\bsize\b|"
    r"\bgespeichert\b|\bstored at\b|"
    r"\b\d+(?:\.\d+)?\s*(?:kb|mb|gb)\b|"
    r"\b\d+(?:[.,]\d+)?\s*(?:sec|sek|min|hour|stund|second|minut)\w*\b)",
    re.IGNORECASE,
)


def _looks_like_metadata(answer: str) -> bool:
    if not answer:
        return False
    return len(_METADATA_HINTS.findall(answer)) >= 2


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

    if not target_username or not external_user_id:
        raise HTTPException(status_code=400, detail="missing_fields")
    if not text and media_type not in ("audio", "audio_failed"):
        raise HTTPException(status_code=400, detail="missing_fields")

    cfg = wa_config.load(target_username)
    sender_for_filter = participant if (is_group and participant) else external_user_id

    pre_decision = wa_filter.evaluate(cfg=cfg, sender_jid=sender_for_filter, is_group=is_group,
                                      text="", skip_keyword=True)
    if not pre_decision.accepted:
        logger.info("WhatsApp pre-filter (%s): user=%s sender=%s",
                    pre_decision.reason, target_username, sender_for_filter)
        return {"ok": True, "filtered": pre_decision.reason}

    transcript, voice_error_msg = await process_voice(
        media_type=media_type, media_data=payload.get("media_data"),
        media_mime=payload.get("media_mime"), media_error=payload.get("media_error"),
        stt_language=cfg.stt_language if cfg.stt_language and cfg.stt_language != "auto" else None,
        target_username=target_username,
    )
    if voice_error_msg:
        ch = get("whatsapp")
        if ch:
            try:
                await ch.send(target_username, external_user_id, voice_error_msg)
            except Exception as e:
                logger.warning("Voice-Error-Reply konnte nicht gesendet werden: %s", e)
        return {"ok": True, "voice_error": True}
    if transcript:
        text = transcript

    decision = wa_filter.evaluate(cfg=cfg, sender_jid=sender_for_filter, is_group=is_group, text=text)
    if not decision.accepted:
        logger.info("WhatsApp gefiltert (%s): user=%s sender=%s",
                    decision.reason, target_username, sender_for_filter)
        return {"ok": True, "filtered": decision.reason}

    event = IncomingEvent(
        channel="whatsapp", external_user_id=external_user_id,
        target_username=target_username, text=text,
        sender_name=payload.get("sender_name"),
        metadata={"is_group": is_group, "is_owner": decision.is_owner,
                  "participant": participant, "voice_mode": cfg.respond_as_voice},
    )
    answer = await handle_incoming(event)
    logger.info("WA incoming user=%s sender=%s text=%r → answer=%r",
                target_username, sender_for_filter, text[:60], (answer[:100] if answer else None))

    if answer:
        ch = get("whatsapp")
        if ch:
            is_fallback = await send_voice_or_text(
                ch, answer=answer, target_username=target_username,
                external_user_id=external_user_id,
                respond_as_voice=cfg.respond_as_voice, voice_name=cfg.voice_name,
                looks_like_metadata=_looks_like_metadata(answer),
            )
            if is_fallback:
                return {"ok": True, "voice_metadata_fallback": True}
    return {"ok": True}
