"""Pro-User-Filter-Config für WhatsApp.

Persistiert als JSON unter `$HH_CONFIG_DIR/whatsapp/<username>.json`.
Default = alles privat erlaubt, Groups aus, keine Listen, kein Keyword.
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
class WhatsAppConfig:
    private_chats_enabled: bool = True
    group_chats_enabled: bool = False
    require_keyword: str = ""
    owner_numbers: list[str] = field(default_factory=list)
    allowed_numbers: list[str] = field(default_factory=list)
    blocked_numbers: list[str] = field(default_factory=list)


def _config_dir() -> Path:
    d = settings.config_dir / "whatsapp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_file(username: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", username)
    return _config_dir() / f"{safe}.json"


def load(username: str) -> WhatsAppConfig:
    f = _config_file(username)
    if not f.exists():
        return WhatsAppConfig()
    try:
        data = json.loads(f.read_text())
    except Exception as e:
        logger.warning("WhatsApp-Config %s nicht lesbar (%s) — Default", username, e)
        return WhatsAppConfig()
    return WhatsAppConfig(
        private_chats_enabled=bool(data.get("private_chats_enabled", True)),
        group_chats_enabled=bool(data.get("group_chats_enabled", False)),
        require_keyword=str(data.get("require_keyword", "") or ""),
        owner_numbers=_normalize_numbers(data.get("owner_numbers", [])),
        allowed_numbers=_normalize_numbers(data.get("allowed_numbers", [])),
        blocked_numbers=_normalize_numbers(data.get("blocked_numbers", [])),
    )


def save(username: str, cfg: WhatsAppConfig) -> WhatsAppConfig:
    cfg.owner_numbers = _normalize_numbers(cfg.owner_numbers)
    cfg.allowed_numbers = _normalize_numbers(cfg.allowed_numbers)
    cfg.blocked_numbers = _normalize_numbers(cfg.blocked_numbers)
    cfg.require_keyword = cfg.require_keyword.strip()
    f = _config_file(username)
    f.write_text(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
    return cfg


def _normalize_numbers(raw) -> list[str]:
    """Whitespace weg, '+'-Prefix entfernt, leere Strings raus, dedupliziert."""
    out: list[str] = []
    seen: set[str] = set()
    for n in raw or []:
        s = re.sub(r"\s+", "", str(n)).lstrip("+")
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out
