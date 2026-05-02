"""Pro-User-Config für Discord-Bot.

Persistiert als JSON unter `$HH_CONFIG_DIR/discord/<safe_username>.json`.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hydrahive.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DiscordConfig:
    bot_token: str = ""
    dm_enabled: bool = True
    mention_enabled: bool = True
    require_keyword: str = ""
    allowed_user_ids: list[str] = field(default_factory=list)
    blocked_user_ids: list[str] = field(default_factory=list)
    allowed_channel_ids: list[str] = field(default_factory=list)
    respond_as_voice: bool = False
    voice_name: str = "German_FriendlyMan"


def _config_dir() -> Path:
    d = settings.discord_config_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_file(username: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", username)
    return _config_dir() / f"{safe}.json"


def load(username: str) -> DiscordConfig:
    f = _config_file(username)
    if not f.exists():
        return DiscordConfig()
    try:
        data = json.loads(f.read_text())
    except Exception as e:
        logger.warning("Discord-Config %s nicht lesbar (%s) — Default", username, e)
        return DiscordConfig()
    return DiscordConfig(
        bot_token=str(data.get("bot_token", "") or ""),
        dm_enabled=bool(data.get("dm_enabled", True)),
        mention_enabled=bool(data.get("mention_enabled", True)),
        require_keyword=str(data.get("require_keyword", "") or ""),
        allowed_user_ids=_normalize_ids(data.get("allowed_user_ids", [])),
        blocked_user_ids=_normalize_ids(data.get("blocked_user_ids", [])),
        allowed_channel_ids=_normalize_ids(data.get("allowed_channel_ids", [])),
        respond_as_voice=bool(data.get("respond_as_voice", False)),
        voice_name=str(data.get("voice_name", "German_FriendlyMan") or "German_FriendlyMan"),
    )


def save(username: str, cfg: DiscordConfig) -> DiscordConfig:
    cfg.allowed_user_ids = _normalize_ids(cfg.allowed_user_ids)
    cfg.blocked_user_ids = _normalize_ids(cfg.blocked_user_ids)
    cfg.allowed_channel_ids = _normalize_ids(cfg.allowed_channel_ids)
    cfg.require_keyword = cfg.require_keyword.strip()
    f = _config_file(username)
    f.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
    return cfg


def _normalize_ids(raw) -> list[str]:
    """Whitespace weg, leere Strings raus, dedupliziert."""
    out: list[str] = []
    seen: set[str] = set()
    for v in raw or []:
        s = str(v).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out
