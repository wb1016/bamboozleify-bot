from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import discord

from .i18n import t

if TYPE_CHECKING:
    from .bot import BamboozleifyBot


def is_mod(interaction: discord.Interaction, mod_role_id: Optional[int]) -> bool:
    """A moderator is anyone with Manage Messages or the configured mod role."""
    user = interaction.user
    permissions = getattr(user, "guild_permissions", None)
    if permissions is not None and permissions.manage_messages:
        return True
    if mod_role_id is not None and isinstance(user, discord.Member):
        return any(role.id == mod_role_id for role in user.roles)
    return False


async def send_mod_log(
    bot: BamboozleifyBot,
    guild: discord.Guild,
    *,
    action: str,
    moderator: discord.abc.User,
    target_id: int,
    reason: Optional[str] = None,
    message_link: Optional[str] = None,
    locale: Optional[discord.Locale] = None,
) -> None:
    """Write an audit entry to the configured mod-log channel. Best effort."""
    cfg = await bot.db.get_config(guild.id)
    if cfg.mod_log_channel_id is None:
        return
    channel = guild.get_channel(cfg.mod_log_channel_id)
    if not isinstance(channel, discord.abc.Messageable):
        return
    embed = discord.Embed(
        title=t(locale, "Anon moderation - {action}", action=action),
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(
        name=t(locale, "Moderator"),
        value=f"{moderator.mention} (`{moderator.id}`)",
        inline=False,
    )
    embed.add_field(name=t(locale, "Target"), value=f"<@{target_id}> (`{target_id}`)", inline=False)
    if reason:
        embed.add_field(name=t(locale, "Reason"), value=reason, inline=False)
    if message_link:
        embed.add_field(name=t(locale, "Message"), value=message_link, inline=False)
    try:
        await channel.send(embed=embed)
    except discord.DiscordException:
        pass
