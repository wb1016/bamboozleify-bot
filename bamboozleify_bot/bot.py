from __future__ import annotations

import logging
import time

import discord
from discord.ext import commands, tasks

from . import config
from .cogs.anon import AnonCog, AnonMessageView
from .cogs.mod import AnonModCog, AnonSetupCog
from .db import Database

log = logging.getLogger(__name__)


class BamboozleifyBot(commands.Bot):
    def __init__(self) -> None:
        # Slash commands and components need no privileged intents.
        intents = discord.Intents.default()
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.db = Database(config.DB_PATH)

    async def setup_hook(self) -> None:
        await self.db.connect()
        # Persistent See OP / Moderation buttons survive restarts via custom_id.
        self.add_view(AnonMessageView(self))
        await self.add_cog(AnonCog(self))
        await self.add_cog(AnonSetupCog(self))
        await self.add_cog(AnonModCog(self))

        if config.GUILD_ID is not None:
            guild = discord.Object(config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        self.retention_purge.start()

    async def on_ready(self) -> None:
        if self.user is not None:
            log.info("logged in as %s (ID: %s)", self.user, self.user.id)

    async def close(self) -> None:
        self.retention_purge.cancel()
        await self.db.close()
        await super().close()

    @tasks.loop(hours=1)
    async def retention_purge(self) -> None:
        cutoff = int(time.time()) - config.RETENTION_DAYS * 86400
        purged = await self.db.purge_authors(cutoff)
        if purged:
            log.info(
                "purged author identities from %d anonymous messages (retention=%dd)",
                purged,
                config.RETENTION_DAYS,
            )

    @retention_purge.before_loop
    async def before_retention_purge(self) -> None:
        await self.wait_until_ready()
