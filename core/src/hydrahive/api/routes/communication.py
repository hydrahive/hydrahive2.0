"""Communication-API — Channel-Liste, WhatsApp-Endpunkte, Bridge-Push."""
from __future__ import annotations

import logging
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
    text = payload.get("text", "")
    is_group = bool(payload.get("is_group", False))
    participant = payload.get("participant")
    if not target_username or not external_user_id or not text:
        raise HTTPException(status_code=400, detail="missing_fields")

    cfg = wa_config.load(target_username)
    sender_for_filter = participant if (is_group and participant) else external_user_id
    decision = wa_filter.evaluate(
        cfg=cfg, sender_jid=sender_for_filter, is_group=is_group, text=text
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
                  "participant": participant},
    )
    answer = await handle_incoming(event)
    if answer:
        ch = get("whatsapp")
        if ch:
            try:
                await ch.send(target_username, external_user_id, answer)
            except Exception as e:
                logger.exception("WhatsApp-Antwort konnte nicht gesendet werden: %s", e)
    return {"ok": True}
