from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.communication import get
from hydrahive.communication.base import ChannelStatus
from hydrahive.communication.whatsapp import config as wa_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/communication", tags=["communication"])


def _status_dict(s: ChannelStatus) -> dict:
    return {"connected": s.connected, "state": s.state, "detail": s.detail,
            "qr_data_url": s.qr_data_url}


def _config_dict(cfg: wa_config.WhatsAppConfig) -> dict:
    return {"private_chats_enabled": cfg.private_chats_enabled,
            "group_chats_enabled": cfg.group_chats_enabled,
            "require_keyword": cfg.require_keyword,
            "owner_numbers": cfg.owner_numbers, "allowed_numbers": cfg.allowed_numbers,
            "blocked_numbers": cfg.blocked_numbers, "respond_as_voice": cfg.respond_as_voice,
            "voice_name": cfg.voice_name, "stt_language": cfg.stt_language}


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
    return _config_dict(wa_config.load(username))


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
        respond_as_voice=bool(payload.get("respond_as_voice", False)),
        voice_name=str(payload.get("voice_name", "German_FriendlyMan") or "German_FriendlyMan"),
        stt_language=str(payload.get("stt_language", "") or "").strip().lower(),
    )
    return _config_dict(wa_config.save(username, cfg))
