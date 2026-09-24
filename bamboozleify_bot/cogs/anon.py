from __future__ import annotations

import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from .. import config
from ..db import AnonMessageRecord
from ..i18n import is_korean, t
from ..utils import is_mod, send_mod_log

if TYPE_CHECKING:
    from ..bot import BamboozleifyBot

MAX_FILES = 10


async def check_can_post(
    bot: BamboozleifyBot, guild_id: int, user_id: int, locale: Optional[discord.Locale] = None
) -> Optional[str]:
    """Return an error message if the user may not post right now, else None."""
    block = await bot.db.get_block(guild_id, user_id)
    if block is not None:
        return t(locale, "You are blocked from sending anonymous messages in this server.")
    cfg = await bot.db.get_config(guild_id)
    if cfg.cooldown_seconds > 0:
        last = await bot.db.get_last_post(guild_id, user_id)
        if last is not None:
            retry_at = last + cfg.cooldown_seconds
            if time.time() < retry_at:
                retry_dt = datetime.fromtimestamp(retry_at, tz=timezone.utc)
                return t(
                    locale,
                    "You are sending anonymous messages too fast - try again {retry}.",
                    retry=discord.utils.format_dt(retry_dt, style="R"),
                )
    return None


class AnonModal(discord.ui.Modal, title="Anonymous message"):
    text = discord.ui.Label(
        text="Message",
        component=discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
            placeholder="What should be sent?",
        ),
    )
    media = discord.ui.Label(
        text="Media (optional)",
        description=f"Photos, a video, or audio. Up to {MAX_FILES} files.",
        component=discord.ui.FileUpload(max_values=MAX_FILES, required=False),
    )

    def __init__(
        self,
        bot: BamboozleifyBot,
        channel: discord.abc.Messageable,
        locale: Optional[discord.Locale] = None,
    ) -> None:
        self.bot = bot
        self.channel = channel
        self.locale = locale
        super().__init__()
        self.title = t(locale, "Anonymous message")
        self.text.text = t(locale, "Message")
        self.text.component.placeholder = t(locale, "What should be sent?")
        self.media.text = t(locale, "Media (optional)")
        self.media.description = t(
            locale, "Photos, a video, or audio. Up to {n} files.", n=MAX_FILES
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        locale = interaction.locale
        assert isinstance(self.text.component, discord.ui.TextInput)
        assert isinstance(self.media.component, discord.ui.FileUpload)
        text_value = self.text.component.value.strip()
        attachments = list(self.media.component.values)

        if not text_value and not attachments:
            await interaction.response.send_message(
                t(locale, "Write some text or attach at least one file."), ephemeral=True
            )
            return

        guild_id = interaction.guild_id
        user_id = interaction.user.id
        if guild_id is None:
            return

        error = await check_can_post(self.bot, guild_id, user_id, locale)
        if error is not None:
            await interaction.response.send_message(error, ephemeral=True)
            return

        files: list[discord.File] = []
        skipped = 0
        for attachment in attachments:
            if attachment.size > config.MAX_FILE_SIZE:
                skipped += 1
                continue
            try:
                files.append(await attachment.to_file())
            except discord.HTTPException:
                skipped += 1

        if not text_value and not files:
            await interaction.response.send_message(
                t(
                    locale,
                    "Every attachment was over the 10 MiB bot upload limit, "
                    "so there is nothing to send.",
                ),
                ephemeral=True,
            )
            return

        try:
            message = await self.channel.send(
                content=text_value or None,
                files=files or None,
                view=AnonMessageView(self.bot, locale),
            )
        except discord.DiscordException as exc:
            await interaction.response.send_message(
                t(locale, "Could not send the message: {exc}", exc=exc), ephemeral=True
            )
            return

        await self.bot.db.add_anon_message(
            message_id=message.id,
            guild_id=guild_id,
            channel_id=interaction.channel_id or 0,
            author_id=user_id,
        )
        await self.bot.db.set_last_post(guild_id, user_id)

        confirmation = t(locale, "Sent anonymously: {url}", url=message.jump_url)
        if skipped:
            confirmation += "\n" + t(
                locale, "-# {n} attachment(s) skipped (over the 10 MiB bot upload limit).", n=skipped
            )
        await interaction.response.send_message(confirmation, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        if interaction.response.is_done():
            await interaction.followup.send(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )


class AnonMessageView(discord.ui.View):
    """Persistent buttons attached to every published anonymous message."""

    def __init__(self, bot: BamboozleifyBot, locale: Optional[discord.Locale] = None) -> None:
        self.bot = bot
        self.locale = locale
        super().__init__(timeout=None)
        if is_korean(locale):
            for child in self.children:
                if child.custom_id == "bamboozleify:see_op":
                    child.label = t(locale, "See OP")
                elif child.custom_id == "bamboozleify:moderation":
                    child.label = t(locale, "Moderation")

    async def _deny_if_not_mod(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if guild is None:
            return False
        cfg = await self.bot.db.get_config(guild.id)
        if not is_mod(interaction, cfg.mod_role_id):
            await interaction.response.send_message(
                t(interaction.locale, "Only moderators can use this."), ephemeral=True
            )
            return False
        return True

    async def _get_record(
        self, interaction: discord.Interaction
    ) -> Optional[AnonMessageRecord]:
        record = await self.bot.db.get_anon_message(interaction.message.id)
        if record is None or record.author_id is None:
            await interaction.response.send_message(
                t(
                    interaction.locale,
                    "I don't know who sent this - the identity may have been purged "
                    "or the record is missing.",
                ),
                ephemeral=True,
            )
            return None
        return record

    @discord.ui.button(label="See OP", emoji="👁️", custom_id="bamboozleify:see_op")
    async def see_op(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None or not await self._deny_if_not_mod(interaction):
            return
        record = await self._get_record(interaction)
        if record is None:
            return
        locale = interaction.locale

        member = guild.get_member(record.author_id)
        if member is not None:
            username = str(member)
        else:
            try:
                user = await self.bot.fetch_user(record.author_id)
                username = str(user)
            except discord.NotFound:
                username = t(locale, "unknown (account may be deleted)")
        posted_at = datetime.fromtimestamp(record.created_at, tz=timezone.utc)

        embed = discord.Embed(
            title=t(locale, "Anonymous message - original poster"),
            color=discord.Color.blurple(),
        )
        embed.add_field(name=t(locale, "User"), value=f"<@{record.author_id}>", inline=True)
        embed.add_field(name=t(locale, "Username"), value=username, inline=True)
        embed.add_field(name=t(locale, "User ID"), value=str(record.author_id), inline=True)
        embed.add_field(name=t(locale, "Posted"), value=discord.utils.format_dt(posted_at, style="R"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Moderation", emoji="🛡️", custom_id="bamboozleify:moderation",
        style=discord.ButtonStyle.secondary,
    )
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None or not await self._deny_if_not_mod(interaction):
            return
        record = await self._get_record(interaction)
        if record is None:
            return
        await interaction.response.send_message(
            t(interaction.locale, "Moderation for {user}", user=f"<@{record.author_id}>"),
            view=ModerationPanel(
                self.bot,
                author_id=record.author_id,
                message_link=interaction.message.jump_url,
                locale=interaction.locale,
            ),
            ephemeral=True,
        )


class ModerationPanel(discord.ui.View):
    """Ephemeral panel with timeout / block / cancel actions."""

    def __init__(
        self,
        bot: BamboozleifyBot,
        *,
        author_id: int,
        message_link: str,
        locale: Optional[discord.Locale] = None,
    ) -> None:
        self.bot = bot
        self.author_id = author_id
        self.message_link = message_link
        self.locale = locale
        super().__init__(timeout=600)
        if is_korean(locale):
            self.timeout_button.label = t(locale, "Timeout")
            self.block_button.label = t(locale, "Block permanently")
            self.cancel_button.label = t(locale, "Cancel")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if guild is None:
            return False
        cfg = await self.bot.db.get_config(guild.id)
        if not is_mod(interaction, cfg.mod_role_id):
            await interaction.response.send_message(
                t(interaction.locale, "Only moderators can use this."), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Timeout", emoji="⏱️", style=discord.ButtonStyle.secondary)
    async def timeout_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        guild = interaction.guild
        if guild is None:
            return
        member = guild.get_member(self.author_id)
        if member is None:
            try:
                member = await guild.fetch_member(self.author_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    t(
                        self.locale,
                        "That user is no longer in this server - use **Block permanently** instead.",
                    ),
                    ephemeral=True,
                )
                return
        if not guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                t(self.locale, "I need the **Moderate Members** permission to time people out."),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            TimeoutModal(
                self.bot, member=member, message_link=self.message_link, locale=self.locale
            )
        )

    @discord.ui.button(
        label="Block permanently", emoji="⛔", style=discord.ButtonStyle.danger
    )
    async def block_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        guild = interaction.guild
        if guild is None:
            return
        await interaction.response.send_modal(
            BlockModal(
                self.bot,
                guild_id=guild.id,
                author_id=self.author_id,
                message_link=self.message_link,
                locale=self.locale,
            )
        )

    @discord.ui.button(label="Cancel", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(
            content=t(self.locale, "Moderation panel closed."), view=None,
        )


class TimeoutModal(discord.ui.Modal, title="Timeout member"):
    duration = discord.ui.Label(
        text="Duration",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="1 hour", value="3600"),
                discord.SelectOption(label="6 hours", value="21600"),
                discord.SelectOption(label="1 day", value="86400"),
                discord.SelectOption(label="3 days", value="259200"),
                discord.SelectOption(label="7 days", value="604800"),
                discord.SelectOption(label="28 days", value="2419200"),
            ],
        ),
    )
    reason = discord.ui.Label(
        text="Reason (optional)",
        component=discord.ui.TextInput(
            style=discord.TextStyle.short, max_length=256, required=False
        ),
    )

    def __init__(
        self,
        bot: BamboozleifyBot,
        *,
        member: discord.Member,
        message_link: str,
        locale: Optional[discord.Locale] = None,
    ) -> None:
        self.bot = bot
        self.member = member
        self.message_link = message_link
        self.locale = locale
        super().__init__()
        self.title = t(locale, "Timeout member")
        self.duration.text = t(locale, "Duration")
        if is_korean(locale):
            for option in self.duration.component.options:
                option.label = t(locale, option.label)
        self.reason.text = t(locale, "Reason (optional)")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        locale = self.locale
        assert isinstance(self.duration.component, discord.ui.Select)
        assert isinstance(self.reason.component, discord.ui.TextInput)
        guild = interaction.guild
        if guild is None:
            return
        seconds = int(self.duration.component.values[0])
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        reason = self.reason.component.value.strip() or None
        try:
            await self.member.timeout(
                until, reason=reason or "anonymous message moderation"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                t(
                    locale,
                    "I could not time that member out (missing permissions or role hierarchy).",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                t(locale, "Timeout failed: {exc}", exc=exc), ephemeral=True
            )
            return
        if seconds % 3600 == 0:
            action = t(locale, "Timeout ({hours}h)", hours=seconds // 3600)
        else:
            action = t(locale, "Timeout ({seconds}s)", seconds=seconds)
        await send_mod_log(
            self.bot,
            guild,
            action=action,
            moderator=interaction.user,
            target_id=self.member.id,
            reason=reason,
            message_link=self.message_link,
            locale=locale,
        )
        await interaction.response.send_message(
            t(
                locale,
                "Timed out {member} until {until}.",
                member=self.member.mention,
                until=discord.utils.format_dt(until, style="R"),
            ),
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        if interaction.response.is_done():
            await interaction.followup.send(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )


class BlockModal(discord.ui.Modal, title="Block from anonymous messages"):
    reason = discord.ui.Label(
        text="Reason (optional)",
        component=discord.ui.TextInput(
            style=discord.TextStyle.short, max_length=256, required=False
        ),
    )

    def __init__(
        self,
        bot: BamboozleifyBot,
        *,
        guild_id: int,
        author_id: int,
        message_link: str,
        locale: Optional[discord.Locale] = None,
    ) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.author_id = author_id
        self.message_link = message_link
        self.locale = locale
        super().__init__()
        self.title = t(locale, "Block from anonymous messages")
        self.reason.text = t(locale, "Reason (optional)")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        locale = self.locale
        assert isinstance(self.reason.component, discord.ui.TextInput)
        reason = self.reason.component.value.strip() or None
        await self.bot.db.add_block(
            self.guild_id, self.author_id, reason, blocked_by=interaction.user.id
        )
        guild = interaction.guild
        if guild is not None:
            await send_mod_log(
                self.bot,
                guild,
                action=t(locale, "Permanent block"),
                moderator=interaction.user,
                target_id=self.author_id,
                reason=reason,
                message_link=self.message_link,
                locale=locale,
            )
        await interaction.response.send_message(
            t(
                locale,
                "Blocked {user} from using anonymous messages in this server. "
                "`/bamboo-mod unblock` reverts it.",
                user=f"<@{self.author_id}>",
            ),
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        if interaction.response.is_done():
            await interaction.followup.send(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                t(interaction.locale, "Something went wrong."), ephemeral=True
            )


class AnonCog(commands.Cog):
    def __init__(self, bot: BamboozleifyBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="bamboo",
        description=app_commands.locale_str("Send an anonymous message to this channel"),
    )
    @app_commands.guild_only()
    async def anon(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        channel = interaction.channel
        if guild is None or channel is None:
            await interaction.response.send_message(
                "This command only works in a server channel.", ephemeral=True
            )
            return

        locale = interaction.locale
        error = await check_can_post(self.bot, guild.id, interaction.user.id, locale)
        if error is None:
            permissions = channel.permissions_for(guild.me)
            if not (permissions.send_messages and permissions.attach_files):
                error = (
                    "I need the **Send Messages** and **Attach Files** permissions "
                    "in this channel."
                )
        if error is not None:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.send_modal(AnonModal(self.bot, channel, locale))
