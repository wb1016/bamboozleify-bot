from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    guild_id            INTEGER PRIMARY KEY,
    mod_role_id         INTEGER,
    mod_log_channel_id  INTEGER,
    cooldown_seconds    INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS anon_messages (
    message_id  INTEGER PRIMARY KEY,
    guild_id    INTEGER NOT NULL,
    channel_id  INTEGER NOT NULL,
    author_id   INTEGER,
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_anon_messages_guild_author
    ON anon_messages (guild_id, author_id);

CREATE TABLE IF NOT EXISTS blocks (
    guild_id    INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    reason      TEXT,
    blocked_by  INTEGER,
    blocked_at  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS cooldowns (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    last_post  INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);
"""


def now() -> int:
    return int(time.time())


@dataclass(frozen=True)
class GuildConfig:
    guild_id: int
    mod_role_id: Optional[int]
    mod_log_channel_id: Optional[int]
    cooldown_seconds: int


@dataclass(frozen=True)
class BlockEntry:
    guild_id: int
    user_id: int
    reason: Optional[str]
    blocked_by: Optional[int]
    blocked_at: int


@dataclass(frozen=True)
class AnonMessageRecord:
    message_id: int
    guild_id: int
    channel_id: int
    author_id: Optional[int]
    created_at: int


def _block_from_row(row: Optional[aiosqlite.Row]) -> Optional[BlockEntry]:
    if row is None:
        return None
    return BlockEntry(
        guild_id=row["guild_id"],
        user_id=row["user_id"],
        reason=row["reason"],
        blocked_by=row["blocked_by"],
        blocked_at=row["blocked_at"],
    )


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ config

    async def get_config(self, guild_id: int) -> GuildConfig:
        async with self.conn.execute(
            "SELECT * FROM config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return GuildConfig(
                guild_id=guild_id,
                mod_role_id=None,
                mod_log_channel_id=None,
                cooldown_seconds=10,
            )
        return GuildConfig(
            guild_id=guild_id,
            mod_role_id=row["mod_role_id"],
            mod_log_channel_id=row["mod_log_channel_id"],
            cooldown_seconds=row["cooldown_seconds"],
        )

    async def _ensure_config(self, guild_id: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO config (guild_id) VALUES (?)", (guild_id,)
        )

    async def set_mod_role(self, guild_id: int, role_id: Optional[int]) -> None:
        await self._ensure_config(guild_id)
        await self.conn.execute(
            "UPDATE config SET mod_role_id = ? WHERE guild_id = ?", (role_id, guild_id)
        )
        await self.conn.commit()

    async def set_mod_log_channel(self, guild_id: int, channel_id: Optional[int]) -> None:
        await self._ensure_config(guild_id)
        await self.conn.execute(
            "UPDATE config SET mod_log_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        await self.conn.commit()

    async def set_cooldown(self, guild_id: int, seconds: int) -> None:
        await self._ensure_config(guild_id)
        await self.conn.execute(
            "UPDATE config SET cooldown_seconds = ? WHERE guild_id = ?",
            (seconds, guild_id),
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ blocks

    async def get_block(self, guild_id: int, user_id: int) -> Optional[BlockEntry]:
        async with self.conn.execute(
            "SELECT * FROM blocks WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return _block_from_row(row)

    async def add_block(
        self,
        guild_id: int,
        user_id: int,
        reason: Optional[str],
        blocked_by: Optional[int],
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO blocks (guild_id, user_id, reason, blocked_by, blocked_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                reason = excluded.reason,
                blocked_by = excluded.blocked_by,
                blocked_at = excluded.blocked_at
            """,
            (guild_id, user_id, reason, blocked_by, now()),
        )
        await self.conn.commit()

    async def remove_block(self, guild_id: int, user_id: int) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM blocks WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def list_blocks(self, guild_id: int) -> list[BlockEntry]:
        async with self.conn.execute(
            "SELECT * FROM blocks WHERE guild_id = ? ORDER BY blocked_at DESC",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_block_from_row(row) for row in rows if row is not None]

    # -------------------------------------------------------------- cooldowns

    async def get_last_post(self, guild_id: int, user_id: int) -> Optional[int]:
        async with self.conn.execute(
            "SELECT last_post FROM cooldowns WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row["last_post"] if row is not None else None

    async def set_last_post(self, guild_id: int, user_id: int, ts: Optional[int] = None) -> None:
        ts = now() if ts is None else ts
        await self.conn.execute(
            """
            INSERT INTO cooldowns (guild_id, user_id, last_post) VALUES (?, ?, ?)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET last_post = excluded.last_post
            """,
            (guild_id, user_id, ts),
        )
        await self.conn.commit()

    # ----------------------------------------------------------- anon messages

    async def add_anon_message(
        self, message_id: int, guild_id: int, channel_id: int, author_id: int
    ) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO anon_messages (message_id, guild_id, channel_id, author_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (message_id, guild_id, channel_id, author_id, now()),
        )
        await self.conn.commit()

    async def get_anon_message(self, message_id: int) -> Optional[AnonMessageRecord]:
        async with self.conn.execute(
            "SELECT * FROM anon_messages WHERE message_id = ?", (message_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return AnonMessageRecord(
            message_id=row["message_id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            author_id=row["author_id"],
            created_at=row["created_at"],
        )

    async def purge_authors(self, before_ts: int) -> int:
        """Null out author identities older than the retention window."""
        cursor = await self.conn.execute(
            "UPDATE anon_messages SET author_id = NULL "
            "WHERE author_id IS NOT NULL AND created_at < ?",
            (before_ts,),
        )
        await self.conn.commit()
        return cursor.rowcount or 0
