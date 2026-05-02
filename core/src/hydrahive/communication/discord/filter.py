"""Filter-Logik für eingehende Discord-Nachrichten.

Reihenfolge:
1. Author in blocked_user_ids → reject
2. DM und dm_enabled=False → reject
3. Mention und mention_enabled=False → reject
4. allowed_user_ids nicht leer und Author nicht drin → reject
5. allowed_channel_ids nicht leer und Channel nicht drin → reject
6. require_keyword gesetzt und nicht in Text → reject
7. Sonst → accept
"""
from __future__ import annotations

from dataclasses import dataclass

from hydrahive.communication.discord.config import DiscordConfig


@dataclass
class FilterResult:
    accepted: bool
    reason: str | None = None


def evaluate(
    *,
    cfg: DiscordConfig,
    author_id: str,
    is_dm: bool,
    channel_id: str,
    text: str,
) -> FilterResult:
    if author_id in cfg.blocked_user_ids:
        return FilterResult(accepted=False, reason="blocked")

    if is_dm and not cfg.dm_enabled:
        return FilterResult(accepted=False, reason="dm_disabled")

    if not is_dm and not cfg.mention_enabled:
        return FilterResult(accepted=False, reason="mention_disabled")

    if cfg.allowed_user_ids and author_id not in cfg.allowed_user_ids:
        return FilterResult(accepted=False, reason="not_in_user_allowlist")

    if cfg.allowed_channel_ids and channel_id not in cfg.allowed_channel_ids:
        return FilterResult(accepted=False, reason="not_in_channel_allowlist")

    if cfg.require_keyword and cfg.require_keyword.lower() not in text.lower():
        return FilterResult(accepted=False, reason="no_keyword")

    return FilterResult(accepted=True)
