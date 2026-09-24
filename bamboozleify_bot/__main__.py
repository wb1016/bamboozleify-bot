from __future__ import annotations

import sys

from . import config
from .bot import BamboozleifyBot


def main() -> None:
    token = config.token()
    if not token:
        sys.exit(
            "error: set BAMBOOZLEIFY_TOKEN (or DISCORD_TOKEN) in the environment "
            "or in a .env file next to pyproject.toml"
        )
    BamboozleifyBot().run(token)


if __name__ == "__main__":
    main()
