from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a .env file next to the project root, if any.

    Kept dependency-free on purpose; existing environment variables win.
    """
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


def _int_env(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"error: {name} must be an integer, got {raw!r}") from None


def token() -> str | None:
    return os.getenv("BAMBOOZLEIFY_TOKEN") or os.getenv("DISCORD_TOKEN")


DB_PATH: str = os.getenv("BAMBOOZLEIFY_DB_PATH", "bamboozleify.db")
GUILD_ID: int | None = _int_env("BAMBOOZLEIFY_GUILD_ID")
RETENTION_DAYS: int = _int_env("BAMBOOZLEIFY_RETENTION_DAYS", 30) or 30

# Discord's current upload limit for bots; larger user uploads are skipped.
MAX_FILE_SIZE: int = 10 * 1024 * 1024
