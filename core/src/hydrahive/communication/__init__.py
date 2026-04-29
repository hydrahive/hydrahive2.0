"""Communication-Layer — Messenger und andere Kommunikationswege.

Public API:
    Channel, ChannelStatus, IncomingEvent  — Datenmodelle / Protocol
    register, get, all_channels            — Registry für Adapter
    handle_incoming                        — Event → Master-Agent → Antwort
"""
from hydrahive.communication.base import Channel, ChannelStatus, IncomingEvent
from hydrahive.communication.registry import all_channels, get, names, register
from hydrahive.communication.router import handle_incoming

__all__ = [
    "Channel", "ChannelStatus", "IncomingEvent",
    "register", "get", "names", "all_channels",
    "handle_incoming",
]
