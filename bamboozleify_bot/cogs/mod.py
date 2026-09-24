from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..i18n import t
from ..utils import send_mod_log

if TYPE_CHECKING:
    from ..bot import BamboozleifyBot

MAX_LIST = 25


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class AnonSetupCog(
    commands.GroupCog,
    group_name="bamboo-setup",
    description=app_commands.locale_str("Configure the anonymous message system"),
):
    def __init__(self, bot: BamboozleifyBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="modrole",
        description=app_commands.locale_str("Set the moderator role for See OP / Moderation buttons"),
    )
    @app_commands.describe(
        role=app_commands.locale_str("Role that can use the See OP / Moderation buttons"),
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_modrole(
        self, interaction: discord.Interaction, role: Optional[discord.Role] = None
    ) -> None:
        """Leave the role empty to clear it."""
        locale = interaction.locale
        assert interaction.guild_id is not None
        await self.bot.db.set_mod_role(interaction.guild_id, role.id if role is not None else None)
        if role is None:
            await interaction.response.send_message(
                t(locale, "Mod role cleared - anyone with **Manage Messages** can moderate."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                t(
                    locale,
                    "Mod role set to {role}. Members holding it can use **See OP** / **Moderation**.",
                    role=role.mention,
                ),
                ephemeral=True,
            )

    @app_commands.command(
        name="modlog",
        description=app_commands.locale_str("Set the channel for moderation audit logs"),
    )
    @app_commands.describe(
        channel=app_commands.locale_str("Channel for the moderation audit log"),
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_modlog(
        self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None
    ) -> None:
        """Leave the channel empty to disable audit logging."""
        locale = interaction.locale
        assert interaction.guild_id is not None
        await self.bot.db.set_mod_log_channel(
            interaction.guild_id, channel.id if channel is not None else None
        )
        if channel is None:
            await interaction.response.send_message(
                t(locale, "Mod-log disabled."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(locale, "Mod-log set to {channel}.", channel=channel.mention), ephemeral=True
            )

    @app_commands.command(
        name="cooldown",
        description=app_commands.locale_str("Seconds between anonymous messages per user (0 disables)"),
    )
    @app_commands.describe(
        seconds=app_commands.locale_str("Wait time in seconds per user (0 disables)"),
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_cooldown(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 86400]
    ) -> None:
        locale = interaction.locale
        assert interaction.guild_id is not None
        await self.bot.db.set_cooldown(interaction.guild_id, seconds)
        if seconds == 0:
            await interaction.response.send_message(
                t(locale, "Cooldown disabled."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(locale, "Cooldown set to {seconds}s per user.", seconds=seconds),
                ephemeral=True,
            )

    @app_commands.command(
        name="show",
        description=app_commands.locale_str("Show the current configuration"),
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_show(self, interaction: discord.Interaction) -> None:
        locale = interaction.locale
        assert interaction.guild_id is not None
        cfg = await self.bot.db.get_config(interaction.guild_id)
        mod_role = f"<@&{cfg.mod_role_id}>" if cfg.mod_role_id is not None else t(locale, "*not set*")
        mod_log = (
            f"<#{cfg.mod_log_channel_id}>"
            if cfg.mod_log_channel_id is not None
            else t(locale, "*disabled*")
        )
        embed = discord.Embed(
            title=t(locale, "Anon bot configuration"), color=discord.Color.blurple()
        )
        embed.add_field(name=t(locale, "Mod role"), value=mod_role)
        embed.add_field(name=t(locale, "Mod log"), value=mod_log)
        embed.add_field(name=t(locale, "Cooldown"), value=t(locale, "{seconds}s", seconds=cfg.cooldown_seconds))
        await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.default_permissions(manage_messages=True)
@app_commands.guild_only()
class AnonModCog(
    commands.GroupCog,
    group_name="bamboo-mod",
    description=app_commands.locale_str("Moderate anonymous message users"),
):
    def __init__(self, bot: BamboozleifyBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="block",
        description=app_commands.locale_str("Permanently block a user from anonymous messages"),
    )
    @app_commands.describe(
        user=app_commands.locale_str("User to block"),
        reason=app_commands.locale_str("Reason for the block"),
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def block(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: Optional[str] = None,
    ) -> None:
        locale = interaction.locale
        assert interaction.guild_id is not None
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                t(locale, "You cannot block yourself."), ephemeral=True
            )
            return
        if user.bot:
            await interaction.response.send_message(
                t(locale, "You cannot block bots."), ephemeral=True
            )
            return
        await self.bot.db.add_block(
            interaction.guild_id, user.id, reason, blocked_by=interaction.user.id
        )
        guild = interaction.guild
        if guild is not None:
            await send_mod_log(
                self.bot,
                guild,
                action=t(locale, "Permanent block"),
                moderator=interaction.user,
                target_id=user.id,
                reason=reason,
                locale=locale,
            )
        await interaction.response.send_message(
            t(
                locale,
                "Blocked {user} from anonymous messages. `/bamboo-mod unblock` reverts it.",
                user=user.mention,
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="unblock",
        description=app_commands.locale_str("Lift an anonymous-message block"),
    )
    @app_commands.describe(
        user=app_commands.locale_str("User to unblock"),
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def unblock(self, interaction: discord.Interaction, user: discord.User) -> None:
        locale = interaction.locale
        assert interaction.guild_id is not None
        removed = await self.bot.db.remove_block(interaction.guild_id, user.id)
        if removed:
            await interaction.response.send_message(
                t(locale, "Unblocked {user}.", user=user.mention), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(locale, "{user} was not blocked.", user=user.mention), ephemeral=True
            )

    @app_commands.command(
        name="blocked",
        description=app_commands.locale_str("List users blocked from anonymous messages"),
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def blocked(self, interaction: discord.Interaction) -> None:
        locale = interaction.locale
        assert interaction.guild_id is not None
        entries = await self.bot.db.list_blocks(interaction.guild_id)
        if not entries:
            await interaction.response.send_message(
                t(locale, "No users are blocked."), ephemeral=True
            )
            return

        lines: list[str] = []
        for entry in entries[:MAX_LIST]:
            blocked_at = discord.utils.format_dt(
                datetime.fromtimestamp(entry.blocked_at, tz=timezone.utc),
                style="R",
            )
            parts = [f"<@{entry.user_id}> (`{entry.user_id}`)"]
            if entry.blocked_by is not None:
                parts.append(f"<@{entry.blocked_by}>")
            parts.append(blocked_at)
            if entry.reason:
                parts.append(entry.reason)
            lines.append(" - ".join(parts))
        if len(entries) > MAX_LIST:
            lines.append(t(locale, "…and {n} more.", n=len(entries) - MAX_LIST))

        embed = discord.Embed(
            title=t(locale, "Blocked users ({n})", n=len(entries)),
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
