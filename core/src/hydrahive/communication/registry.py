"""Modul-Singleton mit allen geladenen Channel-Adaptern.

Befüllt durch `register()` aus den Channel-Modulen heraus, beim Backend-
Start einmalig in `api/main.py::lifespan`.
"""
from __future__ import annotations

import logging

from hydrahive.communication.base import Channel

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Channel] = {}


def register(channel: Channel) -> None:
    if channel.name in _REGISTRY:
        logger.warning("Channel '%s' wird ersetzt", channel.name)
    _REGISTRY[channel.name] = channel
    logger.info("Channel registriert: %s (%s)", channel.name, channel.label)


def get(name: str) -> Channel | None:
    return _REGISTRY.get(name)


def all_channels() -> list[Channel]:
    return list(_REGISTRY.values())


def names() -> list[str]:
    return sorted(_REGISTRY.keys())
