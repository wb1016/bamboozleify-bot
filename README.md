# bamboozleify-bot

Korean service name: **대숲봇**. Anonymous chat proxy bot for Discord. Members run `/bamboo` in a chat channel,
fill in text and media in a private dialog, and the bot posts it as a normal
message - the author's identity is never shown publicly.

Moderation follows the [neo-quesdon](https://github.com/serafuku/neo-quesdon)-style model: identity is stored privately,
revealed only to moderators through an explicit ephemeral action, and every
reveal / timeout / block is written to an audit log.

## Usage

1. `/bamboo` - opens a private modal with a text field and a file upload
   (up to 10 photos / one video / audio, 10 MiB each).
2. Submitting posts the message as plain content + native attachments
   (photos render inline, video/audio get players), with two buttons:
   - **See OP** - moderators only; shows the real author in an ephemeral reply.
   - **Moderation** - moderators only; opens an ephemeral panel to
     **Timeout** (1h–28d, Discord native timeout) or **Block permanently**
     (bot-level blocklist; `/bamboo-mod unblock` reverts).
3. Every moderation action is logged to the configured mod-log channel.

## Setup commands (admins)

| Command | Purpose |
|---|---|
| `/bamboo-setup modrole [role]` | Role allowed to use the mod buttons - pick from the dropdown (empty = anyone with Manage Messages). Assign the role to moderators manually |
| `/bamboo-setup modlog [channel]` | Channel for the moderation audit log (empty = off) |
| `/bamboo-setup cooldown <seconds>` | Per-user cooldown between anon messages (0 = off) |
| `/bamboo-setup show` | Show current config |

## Moderation commands

| Command | Purpose |
|---|---|
| `/bamboo-mod block <user> [reason]` | Proactively block a user |
| `/bamboo-mod unblock <user>` | Lift a block |
| `/bamboo-mod blocked` | List blocked users |

## Running

### With Astral-UV
Requires [uv](https://docs.astral.sh/uv/). No local library checkouts needed -
discord.py comes from PyPI (2.7+ for modal file-upload support).

```bash
uv venv -p 3.14
uv pip install -e .

cp .env.example .env   # then put your bot token in .env
.venv/bin/python -m bamboozleify_bot
```

### With plain Python
```bash
python -m venv
source .venv/bin/activate
pip install -e .

cp .env.example .env   # then put your bot token in .env
python -m bamboozleify_bot
```

Environment variables (all optional except the token):

| Variable | Default | Purpose |
|---|---|---|
| `BAMBOOZLEIFY_TOKEN` / `DISCORD_TOKEN` | - | Bot token (required) |
| `BAMBOOZLEIFY_GUILD_ID` | - | Sync commands to one guild instantly (dev) |
| `BAMBOOZLEIFY_DB_PATH` | `bamboozleify.db` | SQLite path |
| `BAMBOOZLEIFY_RETENTION_DAYS` | `30` | Days before author identities are purged |

## Bot permissions

Send Messages, Attach Files, Moderate Members (for timeouts), View Channels.
No privileged intents are required, and the bot needs no role management -
moderation roles are created and assigned entirely by server admins.

Invite URL permissions integer: `1099511663616`.

## Localization

All UI text is bilingual. Discord reports each user's client locale on every
interaction - when it is Korean (`ko`), buttons, modals, messages, and embeds
render in Korean; every other locale gets English. Command descriptions and
parameter hints are localized at sync time via a `discord.app_commands`
translator. Command *names* (`/bamboo`, `/bamboo-setup`, `/bamboo-mod`) are
not localized.

Strings live in `bamboozleify_bot/i18n.py` (English text doubles as the key;
missing keys fall back to English). Adding another language means adding a
dict + extending `t()` and `KoreanTranslator`.

## Privacy notes

- Author IDs live only in the local SQLite database and are nulled out after
  the retention window (default 30 days).
- Everything a moderator sees (OP identity, moderation panel) is ephemeral -
  visible only to that moderator.
- The public message is posted by the bot account; no user metadata is attached.
