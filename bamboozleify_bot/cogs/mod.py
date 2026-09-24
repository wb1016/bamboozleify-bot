from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ..utils import send_mod_log

if TYPE_CHECKING:
    from ..bot import BamboozleifyBot

MAX_LIST = 25


@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
class AnonSetupCog(commands.GroupCog, group_name="anon-setup", description="Configure the anonymous message system"):
    def __init__(self, bot: BamboozleifyBot) -> None:
        self.bot = bot

    @app_commands.command(name="modrole", description="Set the moderator role for See OP / Moderation buttons")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_modrole(
        self, interaction: discord.Interaction, role: Optional[discord.Role] = None
    ) -> None:
        """Leave the role empty to clear it."""
        assert interaction.guild_id is not None
        await self.bot.db.set_mod_role(interaction.guild_id, role.id if role is not None else None)
        if role is None:
            await interaction.response.send_message(
                "Mod role cleared — anyone with **Manage Messages** can moderate.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"Mod role set to {role.mention}.", ephemeral=True
            )

    @app_commands.command(name="modlog", description="Set the channel for moderation audit logs")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_modlog(
        self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None
    ) -> None:
        """Leave the channel empty to disable audit logging."""
        assert interaction.guild_id is not None
        await self.bot.db.set_mod_log_channel(
            interaction.guild_id, channel.id if channel is not None else None
        )
        if channel is None:
            await interaction.response.send_message(
                "Mod-log disabled.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Mod-log set to {channel.mention}.", ephemeral=True
            )

    @app_commands.command(name="cooldown", description="Seconds between anonymous messages per user (0 disables)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_cooldown(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 86400]
    ) -> None:
        assert interaction.guild_id is not None
        await self.bot.db.set_cooldown(interaction.guild_id, seconds)
        if seconds == 0:
            await interaction.response.send_message("Cooldown disabled.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"Cooldown set to {seconds}s per user.", ephemeral=True
            )

    @app_commands.command(name="show", description="Show the current configuration")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_show(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        cfg = await self.bot.db.get_config(interaction.guild_id)
        mod_role = f"<@&{cfg.mod_role_id}>" if cfg.mod_role_id is not None else "*not set*"
        mod_log = (
            f"<#{cfg.mod_log_channel_id}>" if cfg.mod_log_channel_id is not None else "*disabled*"
        )
        embed = discord.Embed(title="Anon bot configuration", color=discord.Color.blurple())
        embed.add_field(name="Mod role", value=mod_role)
        embed.add_field(name="Mod log", value=mod_log)
        embed.add_field(name="Cooldown", value=f"{cfg.cooldown_seconds}s")
        await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.default_permissions(manage_messages=True)
@app_commands.guild_only()
class AnonModCog(commands.GroupCog, group_name="anon-mod", description="Moderate anonymous message users"):
    def __init__(self, bot: BamboozleifyBot) -> None:
        self.bot = bot

    @app_commands.command(name="block", description="Permanently block a user from anonymous messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def block(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: Optional[str] = None,
    ) -> None:
        assert interaction.guild_id is not None
        if user.id == interaction.user.id:
            await interaction.response.send_message("You cannot block yourself.", ephemeral=True)
            return
        if user.bot:
            await interaction.response.send_message("You cannot block bots.", ephemeral=True)
            return
        await self.bot.db.add_block(
            interaction.guild_id, user.id, reason, blocked_by=interaction.user.id
        )
        guild = interaction.guild
        if guild is not None:
            await send_mod_log(
                self.bot,
                guild,
                action="Permanent block",
                moderator=interaction.user,
                target_id=user.id,
                reason=reason,
            )
        await interaction.response.send_message(
            f"Blocked {user.mention} from anonymous messages. `/anon-mod unblock` reverts it.",
            ephemeral=True,
        )

    @app_commands.command(name="unblock", description="Lift an anonymous-message block")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def unblock(self, interaction: discord.Interaction, user: discord.User) -> None:
        assert interaction.guild_id is not None
        removed = await self.bot.db.remove_block(interaction.guild_id, user.id)
        if removed:
            await interaction.response.send_message(
                f"Unblocked {user.mention}.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{user.mention} was not blocked.", ephemeral=True
            )

    @app_commands.command(name="blocked", description="List users blocked from anonymous messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def blocked(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        entries = await self.bot.db.list_blocks(interaction.guild_id)
        if not entries:
            await interaction.response.send_message(
                "No users are blocked.", ephemeral=True
            )
            return

        lines: list[str] = []
        for entry in entries[:MAX_LIST]:
            blocked_at = discord.utils.format_dt(
                datetime.fromtimestamp(entry.blocked_at, tz=timezone.utc),
                style="R",
            )
            by = f"by <@{entry.blocked_by}>" if entry.blocked_by is not None else ""
            reason = f" — {entry.reason}" if entry.reason else ""
            lines.append(f"<@{entry.user_id}> (`{entry.user_id}`) {by} {blocked_at}{reason}")
        if len(entries) > MAX_LIST:
            lines.append(f"…and {len(entries) - MAX_LIST} more.")

        embed = discord.Embed(
            title=f"Blocked users ({len(entries)})",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
