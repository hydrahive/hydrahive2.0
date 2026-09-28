"""Test-Doubles für die Serververwaltung: Guild, Rolle, Mitglied, Kategorie.

Ergänzt tests/_discord_fakes.py. Die ops_guild/ops_structure/ops_roles/
ops_members-Module greifen nur auf die hier nachgebauten Attribute zu.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import discord

from tests._discord_fakes import BOT_ID, FakeChannel, T0

OWNER_ID = 100


class FakeRole:
    def __init__(self, rid: int, name: str, position: int, *, permissions=None,
                 managed: bool = False, is_default: bool = False, color: int = 0):
        self.id = rid
        self.name = name
        self.position = position
        self.permissions = permissions or discord.Permissions.none()
        self.managed = managed
        self._default = is_default
        self.color = discord.Colour(color)
        self.mentionable = False
        self.hoist = False
        self.edited_with: dict = {}
        self.deleted_with: str | None = None

    def is_default(self) -> bool:
        return self._default

    def __eq__(self, other):
        return isinstance(other, FakeRole) and other.id == self.id

    def __hash__(self):
        return hash(self.id)

    async def edit(self, *, reason: str = "", **kwargs):
        self.edited_with = {**kwargs, "reason": reason}
        for k, v in kwargs.items():
            if k in ("name", "permissions", "mentionable", "hoist"):
                setattr(self, k, v)
            if k == "colour":
                self.color = v
        return self

    async def delete(self, *, reason: str = ""):
        self.deleted_with = reason


class FakeMember:
    def __init__(self, uid: int, name: str, roles: list[FakeRole], *, bot: bool = False,
                 nick: str | None = None):
        self.id = uid
        self.name = name
        self.display_name = nick or name
        self.nick = nick
        self.bot = bot
        self.roles = list(roles)
        self.top_role = max(roles, key=lambda r: r.position)
        self.joined_at = T0
        self.mention = f"<@{uid}>"
        self.actions: list[tuple] = []

    async def edit(self, *, reason: str = "", **kwargs):
        self.actions.append(("edit", kwargs, reason))
        if "nick" in kwargs:
            self.nick = kwargs["nick"]
            self.display_name = kwargs["nick"] or self.name

    async def add_roles(self, *roles, reason: str = ""):
        self.actions.append(("add_roles", roles, reason))
        self.roles.extend(roles)

    async def remove_roles(self, *roles, reason: str = ""):
        self.actions.append(("remove_roles", roles, reason))
        self.roles = [r for r in self.roles if r not in roles]

    async def timeout(self, until, *, reason: str = ""):
        self.actions.append(("timeout", until, reason))

    async def kick(self, *, reason: str = ""):
        self.actions.append(("kick", None, reason))

    async def ban(self, *, reason: str = "", delete_message_days: int = 0):
        self.actions.append(("ban", delete_message_days, reason))


class FakeGuild:
    """Server mit Bot (Rolle 'Bot' auf Position 5), Besitzer (Position 10) und Mitgliedern."""

    def __init__(self, gid: int = 1, name: str = "HydraHive", *, bot_permissions=None):
        self.id = gid
        self.name = name
        self.owner_id = OWNER_ID
        self.member_count = 3
        self.everyone = FakeRole(gid, "@everyone", 0, is_default=True)
        self.bot_role = FakeRole(5, "Bot", 5, permissions=discord.Permissions(administrator=True))
        self.admin_role = FakeRole(10, "Admin", 10, permissions=discord.Permissions(administrator=True))
        self.roles = [self.everyone, self.bot_role, self.admin_role]
        self.me = FakeMember(BOT_ID, "hydrahive", [self.everyone, self.bot_role], bot=True)
        self.me.guild_permissions = bot_permissions or discord.Permissions(administrator=True)
        self.owner = FakeMember(OWNER_ID, "chef", [self.everyone, self.admin_role])
        self.members = [self.me, self.owner]
        self.channels: list = []
        self.categories: list = []
        self.created: list[tuple] = []
        self.bans: list[tuple] = []
        self.unbans: list[tuple] = []

    # --- Lookups ---
    def get_member(self, uid: int):
        return next((m for m in self.members if m.id == uid), None)

    async def fetch_member(self, uid: int):
        m = self.get_member(uid)
        if m is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="nf"), "Unknown Member")
        return m

    def get_role(self, rid: int):
        return next((r for r in self.roles if r.id == rid), None)

    def get_channel(self, cid: int):
        return next((c for c in [*self.channels, *self.categories] if c.id == cid), None)

    # --- Anlegen ---
    async def create_category(self, name, *, reason: str = "", **kwargs):
        cat = SimpleNamespace(id=700 + len(self.categories), name=name, type=discord.ChannelType.category,
                              position=len(self.categories), guild=self, channels=[])
        self.categories.append(cat)
        self.created.append(("category", name, kwargs, reason))
        return cat

    async def create_text_channel(self, name, *, reason: str = "", **kwargs):
        return self._new_channel(discord.ChannelType.text, name, kwargs, reason)

    async def create_forum(self, name, *, reason: str = "", **kwargs):
        return self._new_channel(discord.ChannelType.forum, name, kwargs, reason)

    def _new_channel(self, ctype, name, kwargs, reason):
        ch = FakeChannel(800 + len(self.channels), ctype, name)
        ch.guild = self
        ch.category = kwargs.get("category")
        ch.created_with = {**kwargs, "reason": reason}
        self.channels.append(ch)
        self.created.append((ctype.name, name, kwargs, reason))
        return ch

    async def create_role(self, *, reason: str = "", **kwargs):
        role = FakeRole(900 + len(self.roles), kwargs.get("name", "neu"), 1,
                        permissions=kwargs.get("permissions") or discord.Permissions.none())
        role.created_with = {**kwargs, "reason": reason}
        self.roles.append(role)
        return role

    async def unban(self, user, *, reason: str = ""):
        self.unbans.append((getattr(user, "id", user), reason))

    async def invites(self):
        return []


def add_member(guild: FakeGuild, uid: int, name: str, *roles: FakeRole, bot: bool = False) -> FakeMember:
    m = FakeMember(uid, name, [guild.everyone, *roles], bot=bot)
    guild.members.append(m)
    return m


def install_guild(monkeypatch, tmp_path: Path, guild: FakeGuild, *, admin_ids: list[str] | None = None,
                  username: str = "u", owner_user_ids: list[str] | None = None):
    """Discord-Config mit Serverfreigabe + Fake-Client, der die Guild kennt."""
    from hydrahive.communication import registry
    from hydrahive.communication.discord import config as dc_config
    from hydrahive.settings import settings

    monkeypatch.setitem(settings.__dict__, "discord_config_dir", tmp_path)
    dc_config.save(username, dc_config.DiscordConfig(
        admin_guild_ids=list(admin_ids if admin_ids is not None else [str(guild.id)]),
        owner_user_ids=list(owner_user_ids or [])))
    client = SimpleNamespace(user=SimpleNamespace(id=BOT_ID), guilds=[guild],
                             get_guild=lambda gid: guild if gid == guild.id else None,
                             get_channel=guild.get_channel)
    adapter = SimpleNamespace(name="discord", label="Discord",
                              client_for=lambda u: client if u == username else None)
    monkeypatch.setitem(registry._REGISTRY, "discord", adapter)
    return client
