"""Test-Doubles für die Discord-Agenten-Tools — kein Netz, kein discord.Client.

Die ops_*-Module erkennen Kanäle über `channel.type` (nicht isinstance), daher
reichen schlanke Fakes mit den genutzten Attributen.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import discord

T0 = dt.datetime(2026, 9, 27, 10, 0, tzinfo=dt.timezone.utc)
BOT_ID = 999


def perms(**over) -> discord.Permissions:
    base = dict(view_channel=True, send_messages=True, read_message_history=True,
                send_messages_in_threads=True, manage_threads=False)
    base.update(over)
    return discord.Permissions(**base)


class FakeMessage:
    def __init__(self, mid: int, text: str, author_id: int = 1, name: str = "Alex",
                 bot: bool = False, channel=None):
        self.id = mid
        self.clean_content = text
        self.author = SimpleNamespace(id=author_id, display_name=name, bot=bot)
        self.created_at = T0
        self.edited_at = None
        self.reference = None
        self.attachments: list = []
        self.embeds: list = []
        self.channel = channel
        self.edits: list[dict] = []
        self.pinned = False
        self.deleted = False

    @property
    def jump_url(self) -> str:
        return f"https://discord.com/channels/1/{getattr(self.channel, 'id', 0)}/{self.id}"

    async def edit(self, **kwargs):
        self.edits.append(kwargs)
        self.clean_content = kwargs.get("content", self.clean_content)
        return self

    async def pin(self, reason=None):
        self.pinned = True

    async def unpin(self, reason=None):
        self.pinned = False

    async def delete(self, delay=None):
        self.deleted = True


class FakeChannel:
    def __init__(self, cid: int, ctype: discord.ChannelType, name: str = "kanal",
                 parent_id: int | None = None, permissions: discord.Permissions | None = None,
                 tags: list[discord.ForumTag] | None = None, require_tag: bool = False,
                 messages: list[FakeMessage] | None = None, locked: bool = False):
        self.id = cid
        self.type = ctype
        self.name = name
        self.parent_id = parent_id
        self.guild = SimpleNamespace(id=1, name="FlowKI Club", me=SimpleNamespace(id=BOT_ID))
        self._perms = permissions or perms()
        self.available_tags = tags or []
        self.flags = discord.ChannelFlags._from_value(16 if require_tag else 0)
        self.messages = messages or []
        for m in self.messages:
            m.channel = self
        self.locked = locked
        self.archived = False
        self.applied_tags: list = []
        self.sent: list[dict] = []
        self.created_threads: list[dict] = []
        self.parent = None           # bei Threads: das Eltern-Forum (von link_thread gesetzt)
        self.message_count = len(self.messages)
        self.edit_calls: list[dict] = []
        self.deleted_with: str | None = None

    async def edit(self, **kwargs):
        """Thread.edit / ForumChannel.edit — Aufrufe mitschreiben und anwenden."""
        self.edit_calls.append(kwargs)
        if "available_tags" in kwargs:
            self.available_tags = list(kwargs["available_tags"])
        for key in ("archived", "locked", "applied_tags", "name"):
            if key in kwargs:
                setattr(self, key, kwargs[key])
        return self

    async def delete(self, reason=None):
        self.deleted_with = reason or ""

    def permissions_for(self, _member):
        return self._perms

    async def send(self, content, **kwargs):
        msg = FakeMessage(10_000 + len(self.sent), content, author_id=BOT_ID, bot=True, channel=self)
        self.sent.append({"content": content, **kwargs})
        return msg

    async def fetch_message(self, mid: int):
        for m in self.messages:
            if m.id == mid:
                return m
        raise discord.NotFound(SimpleNamespace(status=404, reason="nf"), "Unknown Message")

    def history(self, limit=100, before=None):
        msgs = sorted(self.messages, key=lambda m: m.id, reverse=True)
        if before is not None:
            msgs = [m for m in msgs if m.id < before.id]

        async def gen():
            for m in msgs[:limit]:
                yield m
        return gen()

    async def create_thread(self, **kwargs):
        self.created_threads.append(kwargs)
        thread = FakeChannel(5000, discord.ChannelType.public_thread, kwargs["name"],
                             parent_id=self.id)
        msg = FakeMessage(5000, kwargs["content"], author_id=BOT_ID, bot=True, channel=thread)
        return SimpleNamespace(thread=thread, message=msg)


def link_thread(thread: FakeChannel, forum: FakeChannel) -> FakeChannel:
    """Thread einem Forum zuordnen (parent/parent_id) wie bei echten Forum-Beiträgen."""
    thread.parent = forum
    thread.parent_id = forum.id
    return thread


class FakeClient:
    def __init__(self, channels: list[FakeChannel]):
        self._channels = {c.id: c for c in channels}
        self.user = SimpleNamespace(id=BOT_ID)

    def get_channel(self, cid):
        return self._channels.get(cid)

    async def fetch_channel(self, cid):
        raise discord.NotFound(SimpleNamespace(status=404, reason="nf"), "Unknown Channel")


def install(monkeypatch, tmp_path: Path, channels: list[FakeChannel], tool_ids: list[str],
            username: str = "u", bot_token: str = "", mod_ids: list[str] | None = None):
    """Discord-Config + Fake-Adapter für `username` einrichten; liefert den Client."""
    from hydrahive.communication import registry
    from hydrahive.communication.discord import config as dc_config
    from hydrahive.settings import settings

    # cached_property: Instanz-__dict__ überschreiben, nicht die Klasse.
    monkeypatch.setitem(settings.__dict__, "discord_config_dir", tmp_path)
    dc_config.save(username, dc_config.DiscordConfig(
        bot_token=bot_token, tool_channel_ids=list(tool_ids),
        moderation_channel_ids=list(mod_ids or [])))
    client = FakeClient(channels)
    adapter = SimpleNamespace(name="discord", label="Discord",
                              client_for=lambda u: client if u == username else None)
    monkeypatch.setitem(registry._REGISTRY, "discord", adapter)
    return client


def ctx(username: str = "u"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="", user_id=username, workspace=Path("/tmp"))
