"""Discord-Channel-Adapter.

Jeder User hat eigenen discord.Client der im FastAPI-asyncio-Loop läuft.
Kein externer Prozess — discord.py spricht direkt mit der Discord-API.

Voraussetzung im Discord Developer Portal:
- "Message Content Intent" aktivieren
- Bot-Permissions: Send Messages, Read Message History, Read Messages/View Channels
"""
from __future__ import annotations

import asyncio
import io
import logging

import discord

from hydrahive.communication.base import ChannelStatus, IncomingEvent
from hydrahive.communication.discord.config import DiscordConfig, load, save
from hydrahive.communication.discord.filter import evaluate
from hydrahive.communication.router import handle_incoming
from hydrahive.settings import settings

logger = logging.getLogger(__name__)


class DiscordAdapter:
    name = "discord"
    label = "Discord"

    def __init__(self) -> None:
        self._clients: dict[str, discord.Client] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._status: dict[str, ChannelStatus] = {}

    async def status(self, username: str) -> ChannelStatus:
        client = self._clients.get(username)
        if client and client.is_ready():
            detail = f"@{client.user}" if client.user else None
            self._status[username] = ChannelStatus(connected=True, state="connected", detail=detail)
        return self._status.get(username, ChannelStatus(connected=False, state="disconnected"))

    async def connect(self, username: str) -> ChannelStatus:
        await self.disconnect(username)

        cfg = load(username)
        if not cfg.bot_token:
            s = ChannelStatus(connected=False, state="disconnected",
                              detail="Kein Bot-Token konfiguriert")
            self._status[username] = s
            return s

        intents = discord.Intents.default()
        intents.dm_messages = True
        intents.guild_messages = True
        intents.message_content = True

        client = discord.Client(intents=intents)
        self._clients[username] = client
        self._status[username] = ChannelStatus(connected=False, state="connecting")

        @client.event
        async def on_ready() -> None:
            detail = f"@{client.user}" if client.user else None
            logger.info("Discord: Bot verbunden als %s für User '%s'", detail, username)
            self._status[username] = ChannelStatus(connected=True, state="connected", detail=detail)

        @client.event
        async def on_message(message: discord.Message) -> None:
            if message.author.bot:
                return
            if client.user and message.author == client.user:
                return

            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = bool(client.user and client.user.mentioned_in(message))

            if not is_dm and not is_mention:
                return

            current_cfg = load(username)
            result = evaluate(
                cfg=current_cfg,
                author_id=str(message.author.id),
                is_dm=is_dm,
                channel_id=str(message.channel.id),
                text=message.content,
            )
            if not result.accepted:
                return

            text = message.content
            if client.user:
                text = (text
                        .replace(f"<@{client.user.id}>", "")
                        .replace(f"<@!{client.user.id}>", "")
                        .strip())

            event = IncomingEvent(
                channel="discord",
                external_user_id=str(message.channel.id),
                target_username=username,
                text=text,
                sender_name=message.author.display_name,
                metadata={
                    "author_id": str(message.author.id),
                    "is_dm": is_dm,
                    "guild_id": str(message.guild.id) if message.guild else None,
                },
            )

            try:
                answer = await handle_incoming(event)
            except Exception as e:
                logger.exception("Discord: handle_incoming fehlgeschlagen: %s", e)
                return

            if not answer:
                return

            if current_cfg.respond_as_voice:
                try:
                    from hydrahive.voice.tts import synthesize_to_ogg
                    clip = await synthesize_to_ogg(answer, voice=current_cfg.voice_name)
                    await message.channel.send(
                        file=discord.File(io.BytesIO(clip), filename="response.ogg")
                    )
                    return
                except Exception as e:
                    logger.warning("Discord TTS fehlgeschlagen, sende Text: %s", e)

            try:
                await message.channel.send(answer)
            except Exception as e:
                logger.warning("Discord: send fehlgeschlagen: %s", e)

        task = asyncio.create_task(self._run_client(client, cfg.bot_token, username))
        self._tasks[username] = task

        await asyncio.sleep(3)
        return await self.status(username)

    async def disconnect(self, username: str) -> None:
        client = self._clients.pop(username, None)
        task = self._tasks.pop(username, None)

        if client and not client.is_closed():
            await client.close()
        if task and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        self._status[username] = ChannelStatus(connected=False, state="disconnected")

    async def send(self, username: str, to: str, text: str) -> None:
        client = self._clients.get(username)
        if not client or not client.is_ready():
            raise RuntimeError("Discord nicht verbunden")
        channel = await client.fetch_channel(int(to))
        await channel.send(text)  # type: ignore[union-attr]

    async def auto_reconnect_all(self) -> None:
        """Alle User mit gespeichertem Token beim Startup reconnecten."""
        await asyncio.sleep(2)
        cfg_dir = settings.discord_config_dir
        if not cfg_dir.exists():
            return
        for cfg_file in cfg_dir.glob("*.json"):
            username = cfg_file.stem
            cfg = load(username)
            if not cfg.bot_token:
                continue
            try:
                await self.connect(username)
                logger.info("Discord: Auto-Reconnect für '%s' getriggert", username)
            except Exception as e:
                logger.warning("Discord: Auto-Reconnect für '%s' fehlgeschlagen: %s", username, e)

    async def aclose(self) -> None:
        """Alle Clients beim Shutdown schließen."""
        for username in list(self._clients):
            await self.disconnect(username)

    async def _run_client(self, client: discord.Client, token: str, username: str) -> None:
        try:
            await client.start(token)
        except discord.LoginFailure as e:
            logger.warning("Discord: Login fehlgeschlagen für '%s': %s", username, e)
            self._status[username] = ChannelStatus(connected=False, state="error", detail=str(e))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Discord: Bot-Task Fehler für '%s': %s", username, e)
            self._status[username] = ChannelStatus(connected=False, state="error", detail=str(e))
        finally:
            if not client.is_closed():
                await client.close()
            # Nur auf disconnected setzen wenn nicht bereits manuell gesetzt
            if self._status.get(username, ChannelStatus(False, "")).state not in ("disconnected",):
                self._status[username] = ChannelStatus(connected=False, state="disconnected")
