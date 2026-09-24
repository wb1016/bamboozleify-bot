# bamboozleify-bot

Anonymous chat proxy bot for Discord. Members run `/anon` in a chat channel,
fill in text and media in a private dialog, and the bot posts it as a normal
message — the author's identity is never shown publicly.

Moderation follows the quesdon-style model: identity is stored privately,
revealed only to moderators through an explicit ephemeral action, and every
reveal / timeout / block is written to an audit log.

## Usage

1. `/anon` — opens a private modal with a text field and a file upload
   (up to 10 photos / one video / audio, 10 MiB each).
2. Submitting posts the message as plain content + native attachments
   (photos render inline, video/audio get players), with two buttons:
   - **See OP** — moderators only; shows the real author in an ephemeral reply.
   - **Moderation** — moderators only; opens an ephemeral panel to
     **Timeout** (1h–28d, Discord native timeout) or **Block permanently**
     (bot-level blocklist; `/anon-mod unblock` reverts).
3. Every moderation action is logged to the configured mod-log channel.

## Setup commands (admins)

| Command | Purpose |
|---|---|
| `/anon-setup modrole [role]` | Role allowed to use the mod buttons (empty = anyone with Manage Messages) |
| `/anon-setup modlog [channel]` | Channel for the moderation audit log (empty = off) |
| `/anon-setup cooldown <seconds>` | Per-user cooldown between anon messages (0 = off) |
| `/anon-setup show` | Show current config |

## Moderation commands

| Command | Purpose |
|---|---|
| `/anon-mod block <user> [reason]` | Proactively block a user |
| `/anon-mod unblock <user>` | Lift a block |
| `/anon-mod blocked` | List blocked users |

## Running

Requires [uv](https://docs.astral.sh/uv/). No local library checkouts needed —
discord.py comes from PyPI (2.7+ for modal file-upload support).

```bash
cd bamboozleify-bot
uv venv -p 3.14
uv pip install -e .

cp .env.example .env   # then put your bot token in .env
.venv/bin/python -m bamboozleify_bot
```

Environment variables (all optional except the token):

| Variable | Default | Purpose |
|---|---|---|
| `BAMBOOZLEIFY_TOKEN` / `DISCORD_TOKEN` | — | Bot token (required) |
| `BAMBOOZLEIFY_GUILD_ID` | — | Sync commands to one guild instantly (dev) |
| `BAMBOOZLEIFY_DB_PATH` | `bamboozleify.db` | SQLite path |
| `BAMBOOZLEIFY_RETENTION_DAYS` | `30` | Days before author identities are purged |

## Bot permissions

Send Messages, Attach Files, Moderate Members (for timeouts), View Channels.
No privileged intents are required.

## Privacy notes

- Author IDs live only in the local SQLite database and are nulled out after
  the retention window (default 30 days).
- Everything a moderator sees (OP identity, moderation panel) is ephemeral —
  visible only to that moderator.
- The public message is posted by the bot account; no user metadata is attached.
