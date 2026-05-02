from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.communication import get
from hydrahive.communication.base import ChannelStatus
from hydrahive.communication.discord import config as dc_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/communication", tags=["communication"])

_TOKEN_MASK = "***"


def _status_dict(s: ChannelStatus) -> dict:
    return {"connected": s.connected, "state": s.state, "detail": s.detail,
            "qr_data_url": None}


def _config_dict(cfg: dc_config.DiscordConfig, *, mask_token: bool = True) -> dict:
    return {
        "bot_token": _TOKEN_MASK if (mask_token and cfg.bot_token) else cfg.bot_token,
        "dm_enabled": cfg.dm_enabled,
        "mention_enabled": cfg.mention_enabled,
        "require_keyword": cfg.require_keyword,
        "allowed_user_ids": cfg.allowed_user_ids,
        "blocked_user_ids": cfg.blocked_user_ids,
        "allowed_channel_ids": cfg.allowed_channel_ids,
        "respond_as_voice": cfg.respond_as_voice,
        "voice_name": cfg.voice_name,
    }


@router.get("/discord/status")
async def discord_status(auth=Depends(require_auth)) -> dict:
    ch = get("discord")
    if not ch:
        raise coded(503, "channel_unavailable", channel="discord")
    username, _ = auth
    return _status_dict(await ch.status(username))


@router.post("/discord/connect")
async def discord_connect(auth=Depends(require_auth)) -> dict:
    ch = get("discord")
    if not ch:
        raise coded(503, "channel_unavailable", channel="discord")
    username, _ = auth
    return _status_dict(await ch.connect(username))


@router.post("/discord/disconnect")
async def discord_disconnect(auth=Depends(require_auth)) -> dict:
    ch = get("discord")
    if not ch:
        raise coded(503, "channel_unavailable", channel="discord")
    username, _ = auth
    await ch.disconnect(username)
    return {"ok": True}


@router.get("/discord/config")
async def discord_get_config(auth=Depends(require_auth)) -> dict:
    username, _ = auth
    return _config_dict(dc_config.load(username), mask_token=True)


@router.put("/discord/config")
async def discord_put_config(payload: dict, auth=Depends(require_auth)) -> dict:
    username, _ = auth
    existing = dc_config.load(username)
    raw_token = str(payload.get("bot_token", "") or "")
    token = existing.bot_token if raw_token == _TOKEN_MASK else raw_token
    cfg = dc_config.DiscordConfig(
        bot_token=token,
        dm_enabled=bool(payload.get("dm_enabled", True)),
        mention_enabled=bool(payload.get("mention_enabled", True)),
        require_keyword=str(payload.get("require_keyword", "") or ""),
        allowed_user_ids=list(payload.get("allowed_user_ids", []) or []),
        blocked_user_ids=list(payload.get("blocked_user_ids", []) or []),
        allowed_channel_ids=list(payload.get("allowed_channel_ids", []) or []),
        respond_as_voice=bool(payload.get("respond_as_voice", False)),
        voice_name=str(payload.get("voice_name", "German_FriendlyMan") or "German_FriendlyMan"),
    )
    return _config_dict(dc_config.save(username, cfg), mask_token=True)
